// Host-side arithmetic model only; this does not execute ARM NEON or the board library.
#include <algorithm>
#include <cstdint>
#include <cstdio>

static unsigned char scalar(unsigned char a,unsigned char b,float t) {
    return static_cast<unsigned char>(a+t*(static_cast<int>(b)-a));
}
static unsigned char q16(unsigned char a,unsigned char b,float t) {
    const uint16_t weight=static_cast<uint16_t>(std::max(0,std::min(65535,static_cast<int>(t*65536+.5f))));
    return static_cast<unsigned char>((uint32_t(a)*(65536-weight)+uint32_t(b)*weight)>>16);
}
int main() {
    unsigned count=0,maximum=0;
    const float fractions[]={0.f,1.f,.1f,.2f,.3f,.4f,.5f,.6f,.7f,.8f,.9f,.99999f};
    for(float t:fractions)for(int a=0;a<256;++a)for(int b=0;b<256;++b) {
        const int difference=std::abs(int(scalar(a,b,t))-int(q16(a,b,t)));
        count+=difference!=0;maximum=std::max(maximum,unsigned(difference));
    }
    std::printf("{\"scope\":\"HOST_FORMULA_MODEL_NOT_ARM_EXECUTION\",\"example\":{\"a\":9,\"b\":4,\"t\":0.6,\"scalar\":%u,\"q16\":%u},\"pairs\":%zu,\"mismatches\":%u,\"max_difference\":%u}\n",unsigned(scalar(9,4,.6f)),unsigned(q16(9,4,.6f)),sizeof(fractions)/sizeof(float)*256*256,count,maximum);
    return scalar(9,4,.6f)==6&&q16(9,4,.6f)==5?0:1;
}
