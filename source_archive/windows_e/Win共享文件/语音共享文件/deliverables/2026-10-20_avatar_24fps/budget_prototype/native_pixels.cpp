// Board-only pixel kernels. Keep the established two-stage affine + resize.
#include <opencv2/core.hpp>
#include <opencv2/imgproc.hpp>
#include <algorithm>
#include <cmath>
#include <cstring>
#include <string>
#include <vector>
#include <cstdint>
#include <ctime>
#include <gst/gst.h>
#include <gst/app/gstappsrc.h>
#include <gst/video/videooverlay.h>
#include <atomic>
#include <mutex>
#include <deque>
#include <chrono>
#ifdef __ARM_NEON
#include <arm_neon.h>
#endif

namespace {
thread_local std::string error;
double cpu_ms(){timespec t;clock_gettime(CLOCK_THREAD_CPUTIME_ID,&t);return t.tv_sec*1000.+t.tv_nsec/1e6;}
struct Pixels {cv::Mat flat, posed, scaled;int mode=1;int resize=cv::INTER_CUBIC;double times[4]={};};
double now_seconds(){return std::chrono::duration<double>(std::chrono::steady_clock::now().time_since_epoch()).count();}
struct Video {
 GstElement* pipeline=nullptr;GstElement* source=nullptr;unsigned long handle=0;int w=0,h=0;
 std::mutex lock;std::deque<double> times;std::atomic<uint64_t> pushed{0},received{0},last_sequence{0};
};
void video_received(GstElement*,GstBuffer* buffer,gpointer owner){
 auto& v=*static_cast<Video*>(owner);double at=now_seconds();std::lock_guard<std::mutex> guard(v.lock);
 v.received++;v.last_sequence=GST_BUFFER_OFFSET(buffer);v.times.push_back(at);if(v.times.size()>240)v.times.pop_front();
}
inline unsigned char clip(float x) {return static_cast<unsigned char>(std::max(0.f,std::min(255.f,x)));}
#ifdef __ARM_NEON
uint8x8_t blend8(uint8x8_t a,uint8x8_t b,uint16_t weight){
 uint16x8_t aa=vmovl_u8(a),bb=vmovl_u8(b);uint16x4_t wa=vdup_n_u16(65535-weight),wb=vdup_n_u16(weight);
 // Sum weights 65535; adding the original value implements a 65536 divisor.
 uint32x4_t lo=vmull_u16(vget_low_u16(aa),wa),hi=vmull_u16(vget_high_u16(aa),wa);
 lo=vmlal_u16(lo,vget_low_u16(bb),wb);hi=vmlal_u16(hi,vget_high_u16(bb),wb);
 lo=vaddw_u16(lo,vget_low_u16(aa));hi=vaddw_u16(hi,vget_high_u16(aa));
 return vmovn_u16(vcombine_u16(vshrn_n_u32(lo,16),vshrn_n_u32(hi,16)));
}
uint8x8_t flat8(uint8x8_t color,uint8x8_t alpha,int background){
 uint16x8_t n=vmull_u8(color,alpha);n=vmlal_u8(n,vdup_n_u8(background),vmvn_u8(alpha));
 n=vaddq_u16(n,vdupq_n_u16(128));n=vaddq_u16(n,vshrq_n_u16(n,8));return vshrn_n_u16(n,8);
}
#endif
}
extern "C" {
const char* aura_pixels_error(){return error.c_str();}
void* aura_video_create(){gst_init(nullptr,nullptr);return new Video();}
int aura_video_attach(void* owner,unsigned long handle,int w,int h){
 if(!owner||!handle||w<=0||h<=0)return -1;auto& v=*static_cast<Video*>(owner);
 std::lock_guard<std::mutex> guard(v.lock);if(v.pipeline&&v.handle==handle)return 0;
 if(v.pipeline){gst_element_set_state(v.pipeline,GST_STATE_NULL);gst_object_unref(v.pipeline);v.pipeline=nullptr;}
 std::string description="appsrc name=input is-live=true format=time block=false max-bytes="+std::to_string(w*h*6)+
  " caps=\"video/x-raw,format=RGB16,width="+std::to_string(w)+",height="+std::to_string(h)+",framerate=24/1,pixel-aspect-ratio=1/1\" ! "
  "queue max-size-buffers=1 max-size-bytes=0 max-size-time=0 leaky=downstream ! "
  "identity name=counter signal-handoffs=true ! ximagesink name=screen sync=false handle-events=false force-aspect-ratio=false";
 GError* err=nullptr;v.pipeline=gst_parse_launch(description.c_str(),&err);
 if(err){error=err->message;g_error_free(err);return -2;}
 v.source=gst_bin_get_by_name(GST_BIN(v.pipeline),"input");GstElement* sink=gst_bin_get_by_name(GST_BIN(v.pipeline),"screen");
 gst_video_overlay_set_window_handle(GST_VIDEO_OVERLAY(sink),handle);gst_object_unref(sink);
 GstElement* counter=gst_bin_get_by_name(GST_BIN(v.pipeline),"counter");g_signal_connect(counter,"handoff",G_CALLBACK(video_received),owner);gst_object_unref(counter);
 v.handle=handle;v.w=w;v.h=h;
 if(gst_element_set_state(v.pipeline,GST_STATE_PLAYING)==GST_STATE_CHANGE_FAILURE){error="Native video pipeline failed";return -3;}
 return 0;
}
void aura_rgb565_copy(const unsigned char* rgb,int w,int h,unsigned char* output){
 int stride=(w*2+3)&~3;
for(int y=0;y<h;++y){
 const unsigned char* src=rgb+y*w*3;unsigned char* dst=output+y*stride;int x=0;
#ifdef __ARM_NEON
 for(;x+8<=w;x+=8){uint8x8x3_t in=vld3_u8(src+x*3);uint16x8_t r=vshlq_n_u16(vmovl_u8(vshr_n_u8(in.val[0],3)),11);uint16x8_t g=vshlq_n_u16(vmovl_u8(vshr_n_u8(in.val[1],2)),5);uint16x8_t b=vmovl_u8(vshr_n_u8(in.val[2],3));vst1q_u8(dst+x*2,vreinterpretq_u8_u16(vorrq_u16(vorrq_u16(r,g),b)));}
#endif
 for(;x<w;++x){uint16_t v=((src[x*3]>>3)<<11)|((src[x*3+1]>>2)<<5)|(src[x*3+2]>>3);dst[x*2]=v&255;dst[x*2+1]=v>>8;}
 if(stride>w*2)std::memset(dst+w*2,0,stride-w*2);
 }
}
int aura_video_push(void* owner,const unsigned char* rgb,int length,uint64_t sequence){
 if(!owner||!rgb)return -1;auto& v=*static_cast<Video*>(owner);
 GstElement* source=nullptr;GstElement* pipeline=nullptr;int w,h;
 {std::lock_guard<std::mutex> guard(v.lock);if(!v.pipeline||!v.source)return 1;source=GST_ELEMENT(gst_object_ref(v.source));pipeline=GST_ELEMENT(gst_object_ref(v.pipeline));w=v.w;h=v.h;}
 if(length!=w*h*3){gst_object_unref(source);gst_object_unref(pipeline);return -2;}
 if(gst_app_src_get_current_level_bytes(GST_APP_SRC(source))>static_cast<guint64>(w*h*6)){gst_object_unref(source);gst_object_unref(pipeline);return 2;}
 int stride=(w*2+3)&~3;GstBuffer* buffer=gst_buffer_new_allocate(nullptr,stride*h,nullptr);GstMapInfo map;
 gst_buffer_map(buffer,&map,GST_MAP_WRITE);
 aura_rgb565_copy(rgb,w,h,map.data);
 gst_buffer_unmap(buffer,&map);GstClock* clock=gst_element_get_clock(pipeline);
 GST_BUFFER_PTS(buffer)=clock?gst_clock_get_time(clock)-gst_element_get_base_time(pipeline):GST_CLOCK_TIME_NONE;
 if(clock)gst_object_unref(clock);GST_BUFFER_DURATION(buffer)=GST_SECOND/24;GST_BUFFER_OFFSET(buffer)=sequence;
 GstFlowReturn flow=gst_app_src_push_buffer(GST_APP_SRC(source),buffer);v.pushed++;
 gst_object_unref(source);gst_object_unref(pipeline);return flow==GST_FLOW_OK?0:-3;
}
int aura_video_stats(void* owner,double* out){
 if(!owner||!out)return -1;auto& v=*static_cast<Video*>(owner);std::lock_guard<std::mutex> guard(v.lock);
 out[0]=v.pushed;out[1]=v.received;out[2]=v.last_sequence;out[3]=0;for(int i=4;i<9;++i)out[i]=0;
 if(v.times.size()>1){std::vector<double> intervals;for(size_t i=1;i<v.times.size();++i)intervals.push_back((v.times[i]-v.times[i-1])*1000);
  out[3]=(v.times.size()-1)/(v.times.back()-v.times.front());std::sort(intervals.begin(),intervals.end());
  out[4]=intervals[intervals.size()/2];out[5]=intervals[std::min(intervals.size()-1,size_t(intervals.size()*.95))];out[6]=intervals[std::min(intervals.size()-1,size_t(intervals.size()*.99))];out[7]=intervals.back();}
 if(!v.times.empty())out[8]=(now_seconds()-v.times.back())*1000;
 if(v.pipeline){GstBus* bus=gst_element_get_bus(v.pipeline);GstMessage* message=gst_bus_pop_filtered(bus,GST_MESSAGE_ERROR);gst_object_unref(bus);
  if(message){GError* e=nullptr;gchar* detail=nullptr;gst_message_parse_error(message,&e,&detail);error=e?e->message:"Video sink error";if(e)g_error_free(e);g_free(detail);gst_message_unref(message);return -2;}}
 return 0;
}
void aura_video_destroy(void* owner){
 if(!owner)return;auto* v=static_cast<Video*>(owner);
 if(v->pipeline){gst_element_set_state(v->pipeline,GST_STATE_NULL);if(v->source)gst_object_unref(v->source);gst_object_unref(v->pipeline);}delete v;
}
void* aura_pixels_create(){cv::setNumThreads(1);return new Pixels();}
void aura_pixels_threads(int threads){cv::setNumThreads(std::max(1,std::min(4,threads)));}
void aura_pixels_resize_mode(void* p,int mode){static_cast<Pixels*>(p)->resize=mode==1?cv::INTER_AREA:mode==2?cv::INTER_LINEAR:cv::INTER_CUBIC;}
void aura_pixels_destroy(void* p){delete static_cast<Pixels*>(p);}
void aura_pixels_mode(void* p,int mode){static_cast<Pixels*>(p)->mode=mode;}
void aura_pixels_times(void* p,double* values){std::memcpy(values,static_cast<Pixels*>(p)->times,4*sizeof(double));}
int aura_blend(const unsigned char* a,const unsigned char* b,unsigned char* out,int n,float t){
 if(!a||!b||!out||n<0||t<0||t>1)return -1;
 if(t==0){std::memcpy(out,a,n);return 0;}if(t==1){std::memcpy(out,b,n);return 0;}
 for(int i=0;i<n;++i)out[i]=static_cast<unsigned char>(a[i]+t*(static_cast<int>(b[i])-a[i]));
 return 0;
}
int aura_pose_blend(void* owner,const unsigned char* rgba,const unsigned char* other,float blend,int w,int h,const double* m,
              int ow,int oh,int r,int g,int b,unsigned char* out){
 try{
  if(!owner||!rgba||!m||!out||w<=0||h<=0||ow<=0||oh<=0)return -1;
  auto& p=*static_cast<Pixels*>(owner);p.flat.create(h,w,CV_8UC3);p.posed.create(h,w,CV_8UC3);
  double start=cpu_ms();const int colors[3]={r,g,b};auto* flat=p.flat.ptr<unsigned char>();
  int first=0;
#ifdef __ARM_NEON
  const uint16_t weight=static_cast<uint16_t>(std::max(0,std::min(65535,static_cast<int>(blend*65536+.5f))));
  for(;first+8<=w*h;first+=8){uint8x8x4_t v=vld4_u8(rgba+4*first);
   if(other){uint8x8x4_t vv=vld4_u8(other+4*first);for(int c=0;c<4;++c)v.val[c]=blend8(v.val[c],vv.val[c],weight);}
   uint8x8x3_t rgb;for(int c=0;c<3;++c)rgb.val[c]=flat8(v.val[c],v.val[3],colors[c]);vst3_u8(flat+3*first,rgb);
  }
#endif
  for(int i=first;i<w*h;++i){const unsigned char* src=rgba+4*i;unsigned char mixed[4];
   if(other){for(int c=0;c<4;++c)mixed[c]=src[c]+blend*(static_cast<int>(other[4*i+c])-src[c]);src=mixed;}
   const int a=src[3];
   for(int c=0;c<3;++c)flat[3*i+c]=static_cast<unsigned char>((src[c]*a+colors[c]*(255-a)+127)/255);
  }
  double flattened=cpu_ms();
  if(p.mode==1){
   cv::Matx23d inverse(m[0],m[1],m[2]+(m[0]+m[1]-1)*.5,m[3],m[4],m[5]+(m[3]+m[4]-1)*.5);
   cv::warpAffine(p.flat,p.posed,inverse,cv::Size(w,h),cv::INTER_LINEAR|cv::WARP_INVERSE_MAP,cv::BORDER_REPLICATE);
   double displacement=0;
   for(int y:{0,h})for(int x:{0,w}){
    displacement=std::max(displacement,std::abs((m[0]-1)*x+m[1]*y+m[2]));
    displacement=std::max(displacement,std::abs(m[3]*x+(m[4]-1)*y+m[5]));
   }
   const int border=std::min(std::max(w,h),static_cast<int>(std::ceil(displacement))+2);
   for(int y=0;y<h;++y){auto* dst=p.posed.ptr<unsigned char>(y);int x=0;
    while(x<w){if(y>=border&&y<h-border&&x>=border&&x<w-border){x=w-border;continue;}
     const double u=m[0]*(x+.5)+m[1]*(y+.5)+m[2],v=m[3]*(x+.5)+m[4]*(y+.5)+m[5];
     if(u<0||u>=w||v<0||v>=h)for(int c=0;c<3;++c)dst[3*x+c]=colors[c];++x;
    }
   }
  }else{
  // Pillow evaluates coordinates at pixel centres. Clamp only centres inside
  // the source; outside centres use the background. No full NumPy mask/scan.
  for(int y=0;y<h;++y){auto* dst=p.posed.ptr<unsigned char>(y);
   const double ax=m[1]*(y+.5)+m[2],ay=m[4]*(y+.5)+m[5];
   for(int x=0;x<w;++x){const double u=m[0]*(x+.5)+ax,v=m[3]*(x+.5)+ay;
    if(u<0||u>=w||v<0||v>=h){for(int c=0;c<3;++c)dst[3*x+c]=colors[c];continue;}
    const float sx=static_cast<float>(u-.5),sy=static_cast<float>(v-.5);
    const int ix=static_cast<int>(std::floor(sx)),iy=static_cast<int>(std::floor(sy));
    const float fx=sx-ix,fy=sy-iy;
    const int x0=std::max(0,std::min(w-1,ix)),x1=std::max(0,std::min(w-1,ix+1));
    const int y0=std::max(0,std::min(h-1,iy)),y1=std::max(0,std::min(h-1,iy+1));
    const auto* top=flat+3*w*y0;const auto* bottom=flat+3*w*y1;
    for(int c=0;c<3;++c){float a=top[3*x0+c]+fx*(top[3*x1+c]-top[3*x0+c]);
     float bb=bottom[3*x0+c]+fx*(bottom[3*x1+c]-bottom[3*x0+c]);
     dst[3*x+c]=clip(std::floor(a+fy*(bb-a)+.5f));
    }
   }
  }
  }
  double posed=cpu_ms();
  if(ow==w&&oh==h)std::memcpy(out,p.posed.data,3*w*h);
  else{cv::Mat target(oh,ow,CV_8UC3,out);cv::resize(p.posed,target,cv::Size(ow,oh),0,0,p.resize);}
  double ended=cpu_ms();p.times[0]=flattened-start;p.times[1]=posed-flattened;p.times[2]=ended-posed;p.times[3]=ended-start;return 0;
 }catch(const std::exception& e){error=e.what();return -2;}
}
int aura_pose(void* p,const unsigned char* rgba,int w,int h,const double* m,int ow,int oh,int r,int g,int b,unsigned char* out){
 return aura_pose_blend(p,rgba,nullptr,0,w,h,m,ow,oh,r,g,b,out);
}
}
