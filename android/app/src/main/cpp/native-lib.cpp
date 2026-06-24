#include <jni.h>
#include <string>
#include <vector>
#include <android/log.h>
#include <algorithm>
#include <cmath>
#include "engine_core.h"

#define LOG_TAG "AI_ENGINE_NATIVE"
#define LOGI(...) __android_log_print(ANDROID_LOG_INFO, LOG_TAG, __VA_ARGS__)
#define LOGE(...) __android_log_print(ANDROID_LOG_ERROR, LOG_TAG, __VA_ARGS__)

static std::unique_ptr<MemoryArena> g_Arena = nullptr;
static std::unique_ptr<Int8ComputationGraph> g_Engine = nullptr;

extern "C" JNIEXPORT void JNICALL
Java_com_example_aiengine_AiModel_initEngine(JNIEnv* env, jobject thiz) {
    LOGI("Initializing native AI kernel...");

    try {
        g_Arena = std::make_unique<MemoryArena>(1024 * 1024);
        g_Engine = std::make_unique<Int8ComputationGraph>(*g_Arena);

        g_Engine->AddNode({ "gemm_layer1", "MatMul", {"input_x", "weights_w1"}, {"internal_out"} });
        g_Engine->AddNode({ "fusion_layer1", "RequantizeReLU", {"internal_out"}, {"output_y"} });

        std::vector<int8_t> weight_data = { 12, -30, 45, -5, 64, -12, 80, 0, -22, -40, 32, 18 };
        g_Engine->RegisterInt8Tensor("weights_w1", {4, 3}, weight_data, 0.02f);

        g_Engine->AllocateIntermediateTensorINT32("internal_out", {1, 3});
        g_Engine->AllocateIntermediateTensorINT8("output_y", {1, 3});

        LOGI("Kernel ready. 1MB memory arena reserved.");
    } catch (const std::exception& e) {
        LOGE("Init failure: %s", e.what());
    }
}

extern "C" JNIEXPORT jfloatArray JNICALL
Java_com_example_aiengine_AiModel_runInference(JNIEnv* env, jobject thiz, jfloatArray input_features) {
    if (!g_Engine) {
        LOGE("Graph not initialized!");
        return nullptr;
    }

    jfloat* raw_input = env->GetFloatArrayElements(input_features, nullptr);
    jsize length = env->GetArrayLength(input_features);

    LOGI("Input vector dimension: %d", length);

    std::vector<int8_t> quantized_input(length);
    float input_scale = 0.04f;
    for (int i = 0; i < length; ++i) {
        float scaled = std::round(raw_input[i] / input_scale);
        quantized_input[i] = static_cast<int8_t>(std::clamp(scaled, -128.0f, 127.0f));
    }
    env->ReleaseFloatArrayElements(input_features, raw_input, JNI_ABORT);

    g_Engine->RegisterInt8Tensor("input_x", {1, static_cast<size_t>(length)}, quantized_input, input_scale);
    g_Engine->Forward();

    auto output_view = g_Engine->GetOutput("output_y");
    float output_scale = g_Engine->GetScale("output_y");

    jfloatArray result = env->NewFloatArray(output_view.data.size());
    std::vector<float> dequantized_output(output_view.data.size());

    for (size_t i = 0; i < output_view.data.size(); ++i) {
        dequantized_output[i] = static_cast<float>(output_view.data[i]) * output_scale;
    }

    env->SetFloatArrayRegion(result, 0, dequantized_output.size(), dequantized_output.data());
    LOGI("Inference complete. Results sent to JVM.");

    return result;
}
