package com.example.aiengine

import android.util.Log
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.withContext

class AiModel {
    private val _inferenceResult = MutableStateFlow<FloatArray>(floatArrayOf())
    val inferenceResult: StateFlow<FloatArray> = _inferenceResult

    private val _isProcessing = MutableStateFlow(false)
    val isProcessing: StateFlow<Boolean> = _isProcessing

    init {
        try {
            System.loadLibrary("native-lib")
            initEngine()
            Log.i("AIEngine", "Native C++ library loaded and initialized")
        } catch (e: UnsatisfiedLinkError) {
            Log.e("AIEngine", "Fatal: cannot load .so library: ${e.message}")
        }
    }

    private external fun initEngine()
    private external fun runInference(input: FloatArray): FloatArray

    suspend fun predictAsync(inputData: FloatArray) {
        if (_isProcessing.value) return

        _isProcessing.value = true
        withContext(Dispatchers.Default) {
            try {
                val result = runInference(inputData)
                _inferenceResult.value = result
            } catch (e: Exception) {
                Log.e("AIEngine", "Inference error: ${e.message}")
            } finally {
                _isProcessing.value = false
            }
        }
    }
}
