$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
$interop='D:\Tools\SolidWorks\SOLIDWORKS\api\redist\SolidWorks.Interop.sldworks.dll'
Add-Type -Path $interop
$code=@'
using System;
using System.Collections.Generic;
using SolidWorks.Interop.sldworks;
public static class TechnicalCadExport {
 public static ISldWorks App;
 public static ModelDoc2 Doc;
 public static Dictionary<string,object> Run(string source,string figures) {
  var result=new Dictionary<string,object>();
  App=(ISldWorks)Activator.CreateInstance(Type.GetTypeFromProgID("SldWorks.Application.30"));
  App.Visible=true;
  App.FrameState=1;
  App.DocumentVisible(true,2);
  result["revision"]=App.RevisionNumber();
  result["opened_before"]=App.GetDocumentCount();
  int error=0,warning=0;
  Doc=App.OpenDoc6(source,2,3,"",ref error,ref warning);
  result["open_error"]=error;result["open_warning"]=warning;
  if(Doc==null)throw new Exception("No assembly document returned");
  int activateError=0;
  App.ActivateDoc3(Doc.GetTitle(),false,1,ref activateError);
  result["activate_error"]=activateError;
  result["title"]=Doc.GetTitle();result["path"]=Doc.GetPathName();
  result["save_flag"]=Doc.GetSaveFlag();
  var assembly=(AssemblyDoc)Doc;
  result["box_m"]=assembly.GetBox(0);
  var rows=new List<Dictionary<string,object>>();
  foreach(object obj in (object[])assembly.GetComponents(false)) {
   var c=(Component2)obj;
   var row=new Dictionary<string,object>();
   row["name"]=c.Name2;row["path"]=c.GetPathName();row["suppression"]=c.GetSuppression();
   row["box_m"]=c.GetBox(false,false);rows.Add(row);
  }
  result["components"]=rows;
  foreach(int pref in new int[]{4,5,6,7,31,32,33,196,197})Doc.SetUserPreferenceToggle(pref,false);
  string[] names={"assembly_isometric","assembly_front","assembly_back","assembly_side"};
  string[] views={"*Isometric","*Front","*Back","*Right"};int[] ids={7,1,2,4};
  var exported=new List<Dictionary<string,object>>();
  for(int i=0;i<names.Length;i++) {
   Doc.ShowNamedView2(views[i],ids[i]);Doc.ViewZoomtofit2();((ModelView)Doc.ActiveView).Scale2*=0.85;Doc.GraphicsRedraw2();System.Threading.Thread.Sleep(300);
   var row=new Dictionary<string,object>();row["name"]=names[i];
   row["success"]=Doc.SaveBMP(System.IO.Path.Combine(figures,names[i]+".bmp"),0,0);
   exported.Add(row);
  }
  result["views"]=exported;
  var parts=new List<Dictionary<string,object>>();
  foreach(string name in new string[]{"Front","Back","base","Base_1","mortor","Screen","camera"}) {
   int pe=0,pw=0,ae=0;
   var pd=App.OpenDoc6(System.IO.Path.Combine(System.IO.Path.GetDirectoryName(source),name+".SLDPRT"),1,3,"",ref pe,ref pw);
   var pr=new Dictionary<string,object>();pr["name"]=name;pr["open_error"]=pe;pr["open_warning"]=pw;
   if(pd==null){parts.Add(pr);continue;}
   App.ActivateDoc3(pd.GetTitle(),false,1,ref ae);
   foreach(int pref in new int[]{4,5,6,7,31,32,33,196,197})pd.SetUserPreferenceToggle(pref,false);
   object bodies=((PartDoc)pd).GetBodies2(-1,true);
   var bounds=new double[]{Double.PositiveInfinity,Double.PositiveInfinity,Double.PositiveInfinity,Double.NegativeInfinity,Double.NegativeInfinity,Double.NegativeInfinity};
   int count=0;bool valid=true;
   if(bodies!=null)foreach(object bo in (object[])bodies){
    count++;var body=(Body2)bo;
    for(int axis=0;axis<3;axis++)foreach(int sign in new int[]{-1,1}) {
     double[] dir=new double[]{0,0,0};dir[axis]=sign;double x=0,y=0,z=0;
     bool ok=body.GetExtremePoint(dir[0],dir[1],dir[2],out x,out y,out z);valid=valid&&ok;
     double value=new double[]{x,y,z}[axis];
     if(sign<0)bounds[axis]=Math.Min(bounds[axis],value);else bounds[axis+3]=Math.Max(bounds[axis+3],value);
    }
   }
   pr["visible_body_count"]=count;pr["extreme_points_valid"]=valid&&count>0;
   if(count>0)pr["exact_local_bounds_m"]=bounds;
   pr["approx_local_bounds_m"]=((PartDoc)pd).GetPartBox(true);
   pd.ShowNamedView2("*Isometric",7);pd.ViewZoomtofit2();((ModelView)pd.ActiveView).Scale2*=0.88;pd.GraphicsRedraw2();System.Threading.Thread.Sleep(200);
   pr["image_export"]=pd.SaveBMP(System.IO.Path.Combine(figures,"part_"+name.ToLowerInvariant()+".bmp"),0,0);
   parts.Add(pr);
  }
  result["parts"]=parts;
  return result;
 }
}
'@
$taskReferences=@($interop)
$taskReferences+=Get-ChildItem -LiteralPath (Join-Path $PSHOME 'ref') -Filter '*.dll' | Select-Object -ExpandProperty FullName
Add-Type -TypeDefinition $code -ReferencedAssemblies $taskReferences
$report=[TechnicalCadExport]::Run((Join-Path $root 'cad\source\together.SLDASM'),(Join-Path $root 'figures'))
$report | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath (Join-Path $root 'qa\solidworks_open.json') -Encoding utf8
$report | ConvertTo-Json -Depth 10
