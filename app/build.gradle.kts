plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.plugin.compose")
}

val uploadStorePath = System.getenv("ANDROID_KEYSTORE_PATH")
val uploadStorePassword = System.getenv("ANDROID_KEYSTORE_PASSWORD")
val uploadKeyAlias = System.getenv("ANDROID_KEY_ALIAS")
val uploadKeyPassword = System.getenv("ANDROID_KEY_PASSWORD")
val hasUploadKey = !uploadStorePath.isNullOrBlank() &&
    !uploadStorePassword.isNullOrBlank() &&
    !uploadKeyAlias.isNullOrBlank() &&
    !uploadKeyPassword.isNullOrBlank()

android {
    namespace = "com.assetwright.app"
    compileSdk = 37

    defaultConfig {
        applicationId = "com.assetwright.app"
        minSdk = 26
        targetSdk = 36
        versionCode = 1
        versionName = "0.1.0"
    }

    signingConfigs {
        create("upload") {
            if (hasUploadKey) {
                storeFile = file(uploadStorePath!!)
                storePassword = uploadStorePassword
                keyAlias = uploadKeyAlias
                keyPassword = uploadKeyPassword
            }
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            if (hasUploadKey) {
                signingConfig = signingConfigs.getByName("upload")
            }
        }
    }

    buildFeatures {
        compose = true
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}

dependencies {
    val composeBom = platform("androidx.compose:compose-bom:2026.09.00")
    implementation(composeBom)
    implementation("androidx.activity:activity-compose:1.13.0")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.ui:ui-tooling-preview")
    debugImplementation("androidx.compose.ui:ui-tooling")
}