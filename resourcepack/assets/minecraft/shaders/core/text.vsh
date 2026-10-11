#version 330
#extension GL_ARB_separate_shader_objects : require

#if !defined(IS_GUI) && !defined(IS_SEE_THROUGH)
#include <minecraft:fog.glsl>
#include <minecraft:sample_lightmap.glsl>
#endif

#include <minecraft:dynamictransforms.glsl>
#include <minecraft:projection.glsl>

layout(location = 0) in vec3 Position;
layout(location = 1) in vec4 Color;
layout(location = 2) in vec2 UV0;
#if !defined(IS_GUI) && !defined(IS_SEE_THROUGH)
layout(location = 3) in ivec2 UV2;
#endif

#if !defined(IS_GUI) && !defined(IS_SEE_THROUGH)
uniform sampler2D Sampler2;
layout(location = 0) out float sphericalVertexDistance;
layout(location = 1) out float cylindricalVertexDistance;
#endif

layout(location = 2) out vec4 vertexColor;
layout(location = 3) out vec2 texCoord0;

void main() {
    vec4 position = ModelViewMat * vec4(Position, 1.0);
#ifdef IS_GUI
    // Dedicated title and shadow colors mark BiomeVisible without moving other text.
    bool biomeTitle = all(lessThan(abs(Color.rgb - vec3(255.0, 255.0, 254.0) / 255.0), vec3(0.001)));
    bool biomeShadow = all(lessThan(abs(Color.rgb - vec3(63.0, 63.0, 62.0) / 255.0), vec3(0.001)));
    if (biomeTitle || biomeShadow) {
        vec2 screen = vec2(2.0 / ProjMat[0][0], -2.0 / ProjMat[1][1]);
        // Title glyphs are at most 200 x 56; vanilla titles use scale 4 and y = -10.
        float scale = min(1.0, min(screen.x * 0.9 / 800.0, screen.y * 0.4 / 224.0));
        vec2 center = floor(screen * 0.5);
        position.x = (position.x - center.x) * scale + center.x;
        position.y = (position.y - center.y + 40.0) * scale + 12.0;
    }
#endif
    gl_Position = ProjMat * position;

#if !defined(IS_GUI) && !defined(IS_SEE_THROUGH)
    sphericalVertexDistance = fog_spherical_distance(Position);
    cylindricalVertexDistance = fog_cylindrical_distance(Position);
    vertexColor = Color * sample_lightmap(Sampler2, UV2);
#else
    vertexColor = Color;
#endif
    texCoord0 = UV0;
}
