#include <jni.h>
#include <stdint.h>
#include <string>
#include <vector>
#include <limits>
#include "meshoptimizer.h"

static void fail(JNIEnv* env, const char* message) {
    jclass ex = env->FindClass("java/lang/IllegalArgumentException");
    if (ex) env->ThrowNew(ex, message);
}

extern "C" JNIEXPORT jbyteArray JNICALL
Java_com_assetwright_app_geometry_MeshoptBridge_decode(
    JNIEnv* env, jobject, jbyteArray compressed, jint count, jint stride,
    jstring mode, jstring filter) {
    if (!compressed || !mode || !filter || count <= 0 || stride <= 0 ||
        (uint64_t)count * (uint64_t)stride > (128ULL << 20)) {
        fail(env, "Invalid or oversized Meshopt buffer (128 MiB limit)");
        return nullptr;
    }
    const jsize input_size = env->GetArrayLength(compressed);
    const char* m = env->GetStringUTFChars(mode, nullptr);
    const char* f = env->GetStringUTFChars(filter, nullptr);
    if (!m || !f) {
        if (m) env->ReleaseStringUTFChars(mode,m);
        if (f) env->ReleaseStringUTFChars(filter,f);
        return nullptr;
    }
    const std::string mode_string(m), filter_string(f);
    env->ReleaseStringUTFChars(mode,m);
    env->ReleaseStringUTFChars(filter,f);
    jbyte* input = env->GetByteArrayElements(compressed, nullptr);
    if (!input) return nullptr;
    std::vector<unsigned char> result((size_t)count*(size_t)stride);
    int status = -1;
    if (mode_string=="ATTRIBUTES") {
        status = meshopt_decodeVertexBuffer(result.data(),(size_t)count,(size_t)stride,
            reinterpret_cast<unsigned char*>(input),(size_t)input_size);
    } else if (mode_string=="TRIANGLES") {
        status = meshopt_decodeIndexBuffer(result.data(),(size_t)count,(size_t)stride,
            reinterpret_cast<unsigned char*>(input),(size_t)input_size);
    } else if (mode_string=="INDICES") {
        status = meshopt_decodeIndexSequence(result.data(),(size_t)count,(size_t)stride,
            reinterpret_cast<unsigned char*>(input),(size_t)input_size);
    }
    env->ReleaseByteArrayElements(compressed,input,JNI_ABORT);
    if (status!=0) {
        fail(env,"Meshopt decoder failed: unsupported mode or invalid compressed stream");
        return nullptr;
    }
    if (filter_string=="OCTAHEDRAL") {
        meshopt_decodeFilterOct(result.data(),(size_t)count,(size_t)stride);
    } else if (filter_string=="QUATERNION") {
        meshopt_decodeFilterQuat(result.data(),(size_t)count,(size_t)stride);
    } else if (filter_string=="EXPONENTIAL") {
        meshopt_decodeFilterExp(result.data(),(size_t)count,(size_t)stride);
    } else if (filter_string=="COLOR") {
        meshopt_decodeFilterColor(result.data(),(size_t)count,(size_t)stride);
    } else if (filter_string!="NONE") {
        fail(env,"Unsupported Meshopt vertex filter");
        return nullptr;
    }
    jbyteArray output=env->NewByteArray((jsize)result.size());
    if (output) env->SetByteArrayRegion(output,0,(jsize)result.size(),
        reinterpret_cast<const jbyte*>(result.data()));
    return output;
}
