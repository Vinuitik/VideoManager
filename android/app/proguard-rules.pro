# Retrofit
-keepattributes Signature
-keepattributes *Annotation*
-keep class retrofit2.** { *; }
-keep interface retrofit2.** { *; }

# Keep model classes so Gson can deserialise them
-keep class com.videomanager.model.** { *; }
