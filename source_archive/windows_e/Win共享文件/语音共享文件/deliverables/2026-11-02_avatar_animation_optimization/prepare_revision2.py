from device_host import *
def main():
 dest=HERE/'candidate_physics_v2/native';dest.mkdir(parents=True,exist_ok=True)
 for p in (HERE/'candidate_physics/native').iterdir():
  if p.is_file():shutil.copyfile(p,dest/p.name)
 p=dest/'secondary_motion.hpp';s=p.read_text()
 start=s.index('   for(int i=0;i<3;++i){');end=s.index('   LayerFrame end;',start)
 s=s[:start]+'''   // Shoulder cap coordinates are from the original opaque sprite atlas:
   // 0059/0060 (left A/B), 0061/0062 (right A/B). Rotate about that attachment,
   // not the original sprite centre, which visibly detaches the sleeve.
   const bool pose_a=branch.label=="腕LA_le"||branch.label=="腕RA_le";
   const double px=left?(pose_a?259.3:-2.2):(pose_a?180.2:69.8);
   const double py=left?(pose_a?-477.6:-526.8):(pose_a?-331.5:-510.5);
   const auto base=original.content.data.coord.data;
   for(int i=0;i<=60;++i){
    auto f=original;f.time=float(i);f.type=2;
    const double degrees=-12.+.4*i,radians=degrees*3.14159265358979323846/180.;
    const double cosine=std::cos(radians),sine=std::sin(radians);
    f.content.data.angle={FieldState::Value,float(degrees)};
    f.content.data.coord={FieldState::Value,{
     float(base[0]+px-(cosine*px-sine*py)),
     float(base[1]+py-(sine*px+cosine*py)),base[2]}};
    branch.frame_list.push_back(std::move(f));
   }
''' + s[end:]
 p.write_text(s,encoding='utf8')
 save(HERE/'candidate_physics_v2/SOURCE_MANIFEST.json',dict(schema='aura-physics-arm-revision2-1',previous_visual_verdict='REJECT_V1_SLEEVE_DETACHMENT',correction='Existing sprite shoulder cap pivot, compensated translation, 0.4 degree keys',files={x.name:sha(x) for x in dest.iterdir() if x.is_file()},production_loaded=False))
 print('Prepared revision2 with shoulder pivots from original sprite atlas')
if __name__=='__main__':main()
