#include <jni.h>

#include <cstdint>
#include <vector>

#include "draco/compression/decode.h"

namespace {
void fail(JNIEnv* env, const char* message) {
    jclass exception = env->FindClass("java/lang/IllegalArgumentException");
    if (exception) env->ThrowNew(exception, message);
}

template <typename T>
bool read_attribute(JNIEnv* env, jobjectArray output, int slot,
                    const draco::PointAttribute& attribute, int count, int components) {
    std::vector<T> values(static_cast<size_t>(count) * components);
    for (int point = 0; point < count; ++point) {
        const auto mapped = attribute.mapped_index(draco::PointIndex(point));
        if (mapped.value() >= attribute.size() ||
            !attribute.ConvertValue<T>(mapped, components, values.data() + point * components)) {
            return false;
        }
    }
    const jsize size = static_cast<jsize>(values.size() * sizeof(T));
    jbyteArray bytes = env->NewByteArray(size);
    if (!bytes) return false;
    env->SetByteArrayRegion(bytes, 0, size, reinterpret_cast<const jbyte*>(values.data()));
    env->SetObjectArrayElement(output, slot, bytes);
    env->DeleteLocalRef(bytes);
    return !env->ExceptionCheck();
}
}  // namespace

extern "C" JNIEXPORT jobjectArray JNICALL
Java_com_assetwright_app_geometry_DracoBridge_decode(
    JNIEnv* env, jobject, jbyteArray compressed, jint point_count,
    jint expected_indices, jintArray attributes) {
    const jsize attributes_size = env->GetArrayLength(attributes);
    if (attributes_size < 3 || attributes_size > 12 || attributes_size % 3 != 0 ||
        point_count < 1 || point_count > 650000 || expected_indices < -1 ||
        expected_indices > 3000000) {
        fail(env, "Invalid or oversized Draco mesh metadata");
        return nullptr;
    }

    jint descriptors[12];
    env->GetIntArrayRegion(attributes, 0, attributes_size, descriptors);
    const jsize compressed_size = env->GetArrayLength(compressed);
    jbyte* input = env->GetByteArrayElements(compressed, nullptr);
    if (!input) return nullptr;
    draco::DecoderBuffer buffer;
    buffer.Init(reinterpret_cast<const char*>(input), compressed_size);
    draco::Decoder decoder;
    auto result = decoder.DecodeMeshFromBuffer(&buffer);
    env->ReleaseByteArrayElements(compressed, input, JNI_ABORT);
    if (!result.ok() || !result.value()) {
        fail(env, "Draco decoder could not read this triangle mesh");
        return nullptr;
    }

    const auto& mesh = *result.value();
    if (mesh.num_points() != static_cast<unsigned>(point_count) ||
        mesh.num_faces() == 0 || mesh.num_faces() > 1000000 ||
        (expected_indices >= 0 && mesh.num_faces() * 3 != static_cast<unsigned>(expected_indices))) {
        fail(env, "Draco mesh counts differ from glTF metadata or exceed Geometry Lab limits");
        return nullptr;
    }

    const int attribute_count = attributes_size / 3;
    jclass bytes_type = env->FindClass("[B");
    if (!bytes_type) return nullptr;
    jobjectArray output = env->NewObjectArray(attribute_count + 1, bytes_type, nullptr);
    if (!output) return nullptr;
    for (int slot = 0; slot < attribute_count; ++slot) {
        const int id = descriptors[slot * 3];
        const int components = descriptors[slot * 3 + 1];
        const int type = descriptors[slot * 3 + 2];
        const auto* attribute = mesh.GetAttributeByUniqueId(id);
        if (!attribute || components < 2 || components > 4 ||
            attribute->num_components() != components) {
            fail(env, "Missing Draco attribute or invalid component count");
            return nullptr;
        }
        bool ok = false;
        switch (type) {
            case 5121: ok = read_attribute<uint8_t>(env, output, slot, *attribute, point_count, components); break;
            case 5123: ok = read_attribute<uint16_t>(env, output, slot, *attribute, point_count, components); break;
            case 5126: ok = read_attribute<float>(env, output, slot, *attribute, point_count, components); break;
        }
        if (!ok) {
            if (!env->ExceptionCheck()) fail(env, "Invalid Draco attribute values or format");
            return nullptr;
        }
    }

    std::vector<uint32_t> indices(static_cast<size_t>(mesh.num_faces()) * 3);
    size_t next = 0;
    for (unsigned i = 0; i < mesh.num_faces(); ++i) {
        for (auto point : mesh.face(draco::FaceIndex(i))) {
            if (point.value() >= mesh.num_points()) {
                fail(env, "Draco triangle references a missing vertex");
                return nullptr;
            }
            indices[next++] = point.value();
        }
    }
    const jsize size = static_cast<jsize>(indices.size() * sizeof(uint32_t));
    jbyteArray bytes = env->NewByteArray(size);
    if (!bytes) return nullptr;
    env->SetByteArrayRegion(bytes, 0, size, reinterpret_cast<const jbyte*>(indices.data()));
    env->SetObjectArrayElement(output, attribute_count, bytes);
    return output;
}
