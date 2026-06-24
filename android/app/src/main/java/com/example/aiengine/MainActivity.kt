package com.example.aiengine

import android.os.Bundle
import android.util.Log
import androidx.activity.ComponentActivity
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

class MainActivity : ComponentActivity() {
    private val aiModel = AiModel()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent { AiInferenceScreen(aiModel) }
    }
}

@Composable
fun AiInferenceScreen(aiModel: AiModel) {
    val result by aiModel.inferenceResult.collectAsState()
    val isProcessing by aiModel.isProcessing.collectAsState()

    MaterialTheme {
        Column(
            modifier = Modifier.fillMaxSize().padding(32.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center
        ) {
            if (isProcessing) {
                CircularProgressIndicator()
                Spacer(modifier = Modifier.height(16.dp))
                Text("C++ engine running INT8 GEMM...")
            } else {
                Text(
                    text = "AI Result: ${result.joinToString(" | ")}",
                    style = MaterialTheme.typography.headlineSmall
                )
                Spacer(modifier = Modifier.height(24.dp))
                Button(onClick = {
                    val mockData = floatArrayOf(1.0f, -0.5f, 2.0f, 0.0f)
                    CoroutineScope(Dispatchers.Main).launch {
                        aiModel.predictAsync(mockData)
                    }
                }) {
                    Text("Run CPU Inference")
                }
            }
        }
    }
}
