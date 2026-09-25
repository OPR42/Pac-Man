#version 330

in vec2 fragTexCoord;
in vec4 fragColor;

uniform sampler2D texture0;

out vec4 finalColor;

void main()
{
    vec4 color = texture(texture0, fragTexCoord) * fragColor;

    float grey = dot(
        color.rgb,
        vec3(0.299, 0.587, 0.114)
    );

    finalColor = vec4(grey, grey, grey, color.a);
}