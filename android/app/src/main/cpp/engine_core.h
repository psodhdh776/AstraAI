#pragma once
#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <cmath>
#include <algorithm>
#include <map>
#include <memory>
#include <cassert>
#include <span>
#include <cstdint>
#include <future>
#include <thread>
#include <random>

// ============================================================================
// 1. MEMORY ARENA
// ============================================================================
class MemoryArena {
public:
    MemoryArena(size_t bytes) {
        m_Buffer.resize(bytes);
        m_Offset = m_Buffer.data();
    }

    uint8_t* Allocate(size_t bytes) {
        size_t aligned_bytes = (bytes + 63) & ~63;
        if (m_Offset + aligned_bytes > m_Buffer.data() + m_Buffer.size()) {
            throw std::runtime_error("Memory Arena Overflow!");
        }
        uint8_t* current_alloc = m_Offset;
        m_Offset += aligned_bytes;
        return current_alloc;
    }

    void Reset() {
        m_Offset = m_Buffer.data();
    }

private:
    std::vector<uint8_t> m_Buffer;
    uint8_t* m_Offset;
};

// ============================================================================
// 2. TENSOR VIEW (non-owning)
// ============================================================================
template<typename T>
struct TensorView {
    std::vector<size_t> shape;
    std::span<T> data;

    inline T& At2D(size_t row, size_t col) {
        return data[row * shape[1] + col];
    }
    inline const T& At2D(size_t row, size_t col) const {
        return data[row * shape[1] + col];
    }
};

// ============================================================================
// 3. QUANTIZED OPS — ARM NEON ACCELERATED
// ============================================================================
class QuantizedOps {
public:
    static void MatMulINT8(const TensorView<int8_t>& A, const TensorView<int8_t>& B, TensorView<int32_t>& C) {
        size_t M = A.shape[0];
        size_t K = A.shape[1];
        size_t N = B.shape[1];

        std::fill(C.data.begin(), C.data.end(), 0);

#if defined(__ARM_NEON) || defined(__ARM_NEON__)
        // ARM NEON SIMD: 16 int8_t per register
        for (size_t i = 0; i < M; ++i) {
            for (size_t k = 0; k < K; ++k) {
                int8x16_t a_vec = vdupq_n_s8(A.At2D(i, k));
                int32x4_t c_acc[4] = { vdupq_n_s32(0), vdupq_n_s32(0), vdupq_n_s32(0), vdupq_n_s32(0) };

                size_t j = 0;
                for (; j + 15 < N; j += 16) {
                    int8x16_t b_vec = vld1q_s8(&B.At2D(k, j));
                    int16x8_t prod_lo = vmull_s8(vget_low_s8(a_vec),  vget_low_s8(b_vec));
                    int16x8_t prod_hi = vmull_s8(vget_high_s8(a_vec), vget_high_s8(b_vec));
                    c_acc[0] = vpadalq_s16(c_acc[0], prod_lo);
                    c_acc[1] = vpadalq_s16(c_acc[1], prod_hi);
                }

                int32_t sums[8];
                vst1q_s32(sums,     c_acc[0]);
                vst1q_s32(sums + 4, c_acc[1]);
                for (int s = 0; s < 8; ++s) {
                    C.At2D(i, (j / 16) * 16 + s) += sums[s];
                }

                for (; j < N; ++j) {
                    C.At2D(i, j) += static_cast<int32_t>(A.At2D(i, k)) * static_cast<int32_t>(B.At2D(k, j));
                }
            }
        }
#else
        // Scalar fallback (x86, non-ARM)
        for (size_t i = 0; i < M; ++i) {
            for (size_t k = 0; k < K; ++k) {
                int32_t a_val = static_cast<int32_t>(A.At2D(i, k));
                for (size_t j = 0; j < N; ++j) {
                    C.At2D(i, j) += a_val * static_cast<int32_t>(B.At2D(k, j));
                }
            }
        }
#endif
    }

    static void RequantizeAndReLU(const TensorView<int32_t>& input, float act_scale, TensorView<int8_t>& output) {
        for (size_t i = 0; i < input.data.size(); ++i) {
            float real_val = static_cast<float>(input.data[i]) * act_scale;
            if (real_val < 0.0f) real_val = 0.0f;
            output.data[i] = static_cast<int8_t>(std::clamp(std::round(real_val), -128.0f, 127.0f));
        }
    }
};

// ============================================================================
// 4. COMPUTATION GRAPH
// ============================================================================
struct OnnxNode {
    std::string name;
    std::string op_type;
    std::vector<std::string> inputs;
    std::vector<std::string> outputs;
};

class Int8ComputationGraph {
public:
    Int8ComputationGraph(MemoryArena& arena) : m_Arena(arena) {}

    void AddNode(const OnnxNode& node) { m_Nodes.push_back(node); }

    void RegisterInt8Tensor(const std::string& name, std::vector<size_t> shape, const std::vector<int8_t>& initial_data, float scale) {
        size_t total_elements = std::accumulate(shape.begin(), shape.end(), 1, std::multiplies<size_t>());
        uint8_t* mem = m_Arena.Allocate(total_elements * sizeof(int8_t));
        std::span<int8_t> span(reinterpret_cast<int8_t*>(mem), total_elements);
        std::copy(initial_data.begin(), initial_data.end(), span.begin());
        m_Int8Registry[name] = TensorView<int8_t>{shape, span};
        m_Scales[name] = scale;
    }

    void AllocateIntermediateTensorINT32(const std::string& name, std::vector<size_t> shape) {
        size_t total_elements = std::accumulate(shape.begin(), shape.end(), 1, std::multiplies<size_t>());
        uint8_t* mem = m_Arena.Allocate(total_elements * sizeof(int32_t));
        std::span<int32_t> span(reinterpret_cast<int32_t*>(mem), total_elements);
        m_Int32Registry[name] = TensorView<int32_t>{shape, span};
    }

    void AllocateIntermediateTensorINT8(const std::string& name, std::vector<size_t> shape) {
        size_t total_elements = std::accumulate(shape.begin(), shape.end(), 1, std::multiplies<size_t>());
        uint8_t* mem = m_Arena.Allocate(total_elements * sizeof(int8_t));
        std::span<int8_t> span(reinterpret_cast<int8_t*>(mem), total_elements);
        m_Int8Registry[name] = TensorView<int8_t>{shape, span};
    }

    void Forward() {
        for (const auto& node : m_Nodes) {
            if (node.op_type == "MatMul") {
                auto& A = m_Int8Registry[node.inputs[0]];
                auto& B = m_Int8Registry[node.inputs[1]];
                auto& C = m_Int32Registry[node.outputs[0]];
                QuantizedOps::MatMulINT8(A, B, C);
                m_Scales[node.outputs[0]] = m_Scales[node.inputs[0]] * m_Scales[node.inputs[1]];
            }
            else if (node.op_type == "RequantizeReLU") {
                auto& input = m_Int32Registry[node.inputs[0]];
                auto& output = m_Int8Registry[node.outputs[0]];
                float input_scale = m_Scales[node.inputs[0]];
                float output_scale = 0.1f;
                m_Scales[node.outputs[0]] = output_scale;
                float act_scale = input_scale / output_scale;
                QuantizedOps::RequantizeAndReLU(input, act_scale, output);
            }
        }
    }

    TensorView<int8_t> GetOutput(const std::string& name) { return m_Int8Registry[name]; }
    float GetScale(const std::string& name) { return m_Scales[name]; }

protected:
    MemoryArena& m_Arena;
    std::vector<OnnxNode> m_Nodes;
    std::map<std::string, TensorView<int8_t>> m_Int8Registry;
    std::map<std::string, TensorView<int32_t>> m_Int32Registry;
    std::map<std::string, float> m_Scales;
};

// ============================================================================
// 5. THREADED PARALLEL GRAPH EXECUTOR (std::async thread pool)
// ============================================================================
class ThreadedInt8Graph : public Int8ComputationGraph {
public:
    using Int8ComputationGraph::Int8ComputationGraph;

    void ForwardParallel() {
        std::vector<std::future<void>> tasks;

        for (const auto& node : m_Nodes) {
            if (node.op_type == "MatMul") {
                tasks.push_back(std::async(std::launch::async, [this, node]() {
                    auto& A = m_Int8Registry[node.inputs[0]];
                    auto& B = m_Int8Registry[node.inputs[1]];
                    auto& C = m_Int32Registry[node.outputs[0]];
                    QuantizedOps::MatMulINT8(A, B, C);
                    m_Scales[node.outputs[0]] = m_Scales[node.inputs[0]] * m_Scales[node.inputs[1]];
                }));
            }
            else if (node.op_type == "RequantizeReLU") {
                // Synchronization point: wait for all prior MatMul tasks
                for (auto& t : tasks) {
                    t.wait();
                }
                tasks.clear();

                auto& input = m_Int32Registry[node.inputs[0]];
                auto& output = m_Int8Registry[node.outputs[0]];
                float input_scale = m_Scales[node.inputs[0]];
                float output_scale = 0.1f;
                m_Scales[node.outputs[0]] = output_scale;
                QuantizedOps::RequantizeAndReLU(input, input_scale / output_scale, output);
            }
        }
        // Drain remaining tasks
        for (auto& t : tasks) {
            t.wait();
        }
    }
};

// ============================================================================
// 6. KV-CACHE (Key-Value cache for autoregressive LLM inference)
// ============================================================================
class KVCache {
public:
    std::vector<float> keys;
    std::vector<float> values;
    size_t seq_len = 0;

    void Append(const std::vector<float>& new_k, const std::vector<float>& new_v) {
        keys.insert(keys.end(), new_k.begin(), new_k.end());
        values.insert(values.end(), new_v.begin(), new_v.end());
        seq_len++;
    }

    void Clear() {
        keys.clear();
        values.clear();
        seq_len = 0;
    }
};

// ============================================================================
// 7. GENERATIVE OPS (Softmax + Sampling for LLM)
// ============================================================================
class GenerativeOps {
public:
    // Numerically stable Softmax (subtracts max before exp to prevent overflow)
    static void Softmax(std::vector<float>& logits) {
        if (logits.empty()) return;
        float max_l = *std::max_element(logits.begin(), logits.end());
        float sum_exp = 0.0f;
        for (float& x : logits) {
            x = std::exp(x - max_l);
            sum_exp += x;
        }
        for (float& x : logits) {
            x /= sum_exp;
        }
    }

    // Greedy: token index with highest probability
    static int ArgMax(const std::vector<float>& probs) {
        return static_cast<int>(std::distance(probs.begin(),
            std::max_element(probs.begin(), probs.end())));
    }

    // Temperature-scaled sampling (creativity control)
    static int SampleWithTemperature(const std::vector<float>& logits, float temp) {
        std::vector<float> scaled = logits;
        for (float& x : scaled) x /= temp;
        Softmax(scaled);
        float r = static_cast<float>(std::rand()) / RAND_MAX;
        float cumulative = 0.0f;
        for (size_t i = 0; i < scaled.size(); ++i) {
            cumulative += scaled[i];
            if (r < cumulative) return static_cast<int>(i);
        }
        return static_cast<int>(scaled.size()) - 1;
    }
};

// ============================================================================
// 8. ADVANCED LLM SAMPLER (Temperature + Top-K + Top-P / Nucleus)
// ============================================================================
struct TokenProb {
    int id;
    float prob;
};

class LlmSampler {
public:
    static int Sample(std::vector<float>& logits, float temperature, int top_k, float top_p, std::mt19937& gen) {
        // 1. Temperature scaling
        if (temperature > 0.0f) {
            for (float& logit : logits) logit /= temperature;
        }

        // 2. Stable Softmax -> probabilities
        float max_l = *std::max_element(logits.begin(), logits.end());
        float sum_exp = 0.0f;
        std::vector<TokenProb> token_probs(logits.size());
        for (size_t i = 0; i < logits.size(); ++i) {
            float e = std::exp(logits[i] - max_l);
            token_probs[i] = { static_cast<int>(i), e };
            sum_exp += e;
        }
        for (auto& tp : token_probs) tp.prob /= sum_exp;

        // 3. Sort descending by probability (for Top-K / Top-P)
        std::sort(token_probs.begin(), token_probs.end(),
            [](const TokenProb& a, const TokenProb& b) { return a.prob > b.prob; });

        // 4. Top-K filter
        if (top_k > 0 && top_k < static_cast<int>(token_probs.size())) {
            token_probs.resize(top_k);
        }

        // 5. Top-P (Nucleus) filter
        if (top_p > 0.0f && top_p < 1.0f) {
            float cumulative = 0.0f;
            size_t cutoff = token_probs.size();
            for (size_t i = 0; i < token_probs.size(); ++i) {
                cumulative += token_probs[i].prob;
                if (cumulative >= top_p) { cutoff = i + 1; break; }
            }
            token_probs.resize(cutoff);
        }

        // 6. Renormalize after filtering
        float new_sum = 0.0f;
        for (const auto& tp : token_probs) new_sum += tp.prob;
        if (new_sum > 0.0f) {
            for (auto& tp : token_probs) tp.prob /= new_sum;
        }

        // 7. Categorical (weighted random) selection
        std::uniform_real_distribution<float> dis(0.0f, 1.0f);
        float r = dis(gen);
        float cur = 0.0f;
        for (const auto& tp : token_probs) {
            cur += tp.prob;
            if (r <= cur) return tp.id;
        }
        return token_probs.front().id;
    }
};

// ============================================================================
// 9. EXTREME SAMPLER — QuickSelect O(V) + Loop Fusion + Paged KVCache
// ============================================================================
struct AlignedToken {
    int32_t id;
    float logit;
};

class ExtremeSampler {
public:
    static int32_t Sample(std::vector<float>& raw_logits, float temperature,
                          int32_t top_k, float top_p, std::mt19937& gen) {
        size_t V = raw_logits.size();
        std::vector<AlignedToken> tokens(V);

        // 1. Loop fusion: temperature + max in one pass
        float max_l = -std::numeric_limits<float>::infinity();
        float inv_temp = (temperature > 0.0f) ? (1.0f / temperature) : 1.0f;
        for (size_t i = 0; i < V; ++i) {
            float l = raw_logits[i] * inv_temp;
            tokens[i] = { static_cast<int32_t>(i), l };
            if (l > max_l) max_l = l;
        }

        // 2. QuickSelect O(V): nth_element for Top-K
        if (top_k > 0 && top_k < static_cast<int32_t>(V)) {
            std::nth_element(tokens.begin(), tokens.begin() + top_k, tokens.end(),
                [](const AlignedToken& a, const AlignedToken& b) { return a.logit > b.logit; });
            tokens.resize(top_k);
        }

        // 3. Full sort only on the small K subset O(K log K)
        std::sort(tokens.begin(), tokens.end(),
            [](const AlignedToken& a, const AlignedToken& b) { return a.logit > b.logit; });

        // 4. Softmax on truncated set
        float sum_exp = 0.0f;
        for (auto& t : tokens) {
            t.logit = std::exp(t.logit - max_l);
            sum_exp += t.logit;
        }

        // 5. Top-P + categorical in one pass (no division per element)
        std::uniform_real_distribution<float> dis(0.0f, 1.0f);
        float cutoff = dis(gen) * sum_exp;
        float cur = 0.0f;
        float sum_inv = 1.0f / sum_exp;

        for (const auto& t : tokens) {
            cur += t.logit;
            if (cur >= cutoff) return t.id;
            if (top_p > 0.0f && top_p < 1.0f) {
                if (cur * sum_inv >= top_p) return t.id;
            }
        }
        return tokens.front().id;
    }
};

// ============================================================================
// 10. PAGED KV-CACHE (Block-based attention cache)
// ============================================================================
struct CacheBlock {
    std::vector<float> keys;
    std::vector<float> values;
};

class PagedKVCache {
public:
    size_t block_size;
    size_t num_layers;
    std::vector<std::vector<CacheBlock>> blocks;

    PagedKVCache(size_t layers, size_t bsize)
        : num_layers(layers), block_size(bsize) {
        blocks.resize(layers);
    }

    void Append(size_t layer, const std::vector<float>& k, const std::vector<float>& v) {
        auto& blks = blocks[layer];
        if (blks.empty() || blks.back().keys.size() >= block_size) {
            blks.push_back({std::vector<float>(), std::vector<float>()});
        }
        auto& bk = blks.back();
        bk.keys.insert(bk.keys.end(), k.begin(), k.end());
        bk.values.insert(bk.values.end(), v.begin(), v.end());
    }

    void Clear() {
        for (auto& blk : blocks) blk.clear();
    }

    size_t TotalTokens() const {
        size_t n = 0;
        for (const auto& blk : blocks)
            for (const auto& cb : blk)
                n += cb.keys.size();
        return n;
    }
};

// ============================================================================
// 11. CONTINUOUS BATCHING SCHEDULER
// ============================================================================
enum class RequestStatus { WAITING, RUNNING, FINISHED };

struct SequenceRequest {
    int32_t id;
    std::vector<int32_t> tokens;
    RequestStatus status = RequestStatus::WAITING;
    size_t max_tokens = 0;
    bool has_eos = false;
};

class ContinuousBatchScheduler {
public:
    size_t max_batch_size;

    ContinuousBatchScheduler(size_t max_batch) : max_batch_size(max_batch) {}

    void AddRequest(const SequenceRequest& req) {
        m_WaitingQueue.push_back(req);
    }

    void StepGeneration(std::mt19937& gen) {
        // Fill active batch from waiting queue
        while (m_ActiveBatch.size() < max_batch_size && !m_WaitingQueue.empty()) {
            auto& next = m_WaitingQueue.front();
            next.status = RequestStatus::RUNNING;
            m_ActiveBatch.push_back(std::move(next));
            m_WaitingQueue.erase(m_WaitingQueue.begin());
        }
        if (m_ActiveBatch.empty()) return;

        for (auto it = m_ActiveBatch.begin(); it != m_ActiveBatch.end(); ) {
            std::uniform_int_distribution<int32_t> dist(10, 500);
            int32_t tok = dist(gen);
            it->tokens.push_back(tok);

            bool done = it->tokens.size() >= it->max_tokens || (tok % 47 == 0);
            if (done) {
                it->status = RequestStatus::FINISHED;
                m_Finished.push_back(std::move(*it));
                it = m_ActiveBatch.erase(it);
            } else {
                ++it;
            }
        }
    }

    bool HasWork() const {
        return !m_ActiveBatch.empty() || !m_WaitingQueue.empty();
    }

    const auto& Finished() const { return m_Finished; }

private:
    std::vector<SequenceRequest> m_WaitingQueue;
    std::vector<SequenceRequest> m_ActiveBatch;
    std::vector<SequenceRequest> m_Finished;
};
