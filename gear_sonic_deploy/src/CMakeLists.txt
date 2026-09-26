# TRTInference wraps TensorRT; only build it for the TensorRT backend.
if(NOT USE_ORT_INFERENCE)
  add_subdirectory(TRTInference)
endif()
add_subdirectory(g1)
add_subdirectory(audio_thread)
