// One-time composition of installed imagegen pigment. No network or env reads.
// Candidate is consumed in place; reruns refuse the already finished output.
'use strict';
const fs = require('node:fs'), zlib = require('node:zlib'), crypto = require('node:crypto');
const {decode, thumbnail} = require('../gathering/thumbnail.js');
const hash = b => crypto.createHash('sha256').update(b).digest('hex');
const ancestorBytes = fs.readFileSync('artifacts/line-4/wall-v17.png');
const candidateBytes = fs.readFileSync('artifacts/line-4/wall-v18.png');
if (hash(ancestorBytes) !== '03d94829acbe2e012ab6356fbca8b888b6a2ffd4682f72c3f2bb1e28e27e952d') throw Error('wrong ancestor');
const old = decode(ancestorBytes), motif = decode(candidateBytes);
if (old.width !== 1254 || old.height !== 1254 || old.channels !== 3 || motif.width === 1254) throw Error('unexpected input');
// Find the generated isolated pigment on white, then downsample its coverage.
let box = [motif.width, motif.height, -1, -1];
for(let y=0;y<motif.height;y++) for(let x=0;x<motif.width;x++) {
  const p=(y*motif.width+x)*motif.channels;
  if(motif.pixels[p]<200 && motif.pixels[p+1]<160 && motif.pixels[p+2]<160)
    box=[Math.min(box[0],x),Math.min(box[1],y),Math.max(box[2],x),Math.max(box[3],y)];
}
if(box[2]<box[0]) throw Error('empty motif');
const width=180, height=Math.round(width*(box[3]-box[1]+1)/(box[2]-box[0]+1));
const left=510, top=170;
if(height>55) throw Error('unexpected motif proportions');
const pixels=Buffer.from(old.pixels); let changed=0;
for(let y=0;y<height;y++) for(let x=0;x<width;x++) {
  const x0=box[0]+Math.floor(x*(box[2]-box[0]+1)/width), x1=box[0]+Math.floor((x+1)*(box[2]-box[0]+1)/width);
  const y0=box[1]+Math.floor(y*(box[3]-box[1]+1)/height), y1=box[1]+Math.floor((y+1)*(box[3]-box[1]+1)/height);
  let red=0, black=0, count=0;
  for(let sy=y0;sy<y1;sy++) for(let sx=x0;sx<x1;sx++) {
    const p=(sy*motif.width+sx)*motif.channels;
    const [r,g,b]=motif.pixels.subarray(p,p+3); count++;
    if(g>205 || b>205) continue;
    const coverage=Math.max(0,Math.min(1,(235-g)/180));
    if(r>g*1.35 && r>75) red+=coverage; else black+=coverage;
  }
  const a=(red+black)/count*0.85;
  if(a<0.025) continue;
  const target=red>black?[133,52,23]:[48,35,24];
  const p=((top+y)*old.width+left+x)*3;
  const previous=Buffer.from(pixels.subarray(p,p+3));
  for(let c=0;c<3;c++) pixels[p+c]=Math.round(pixels[p+c]*(1-a)+target[c]*a);
  if(!previous.equals(pixels.subarray(p,p+3))) changed++;
}
function crc32(b){let c=0xffffffff;for(const v of b){c^=v;for(let i=0;i<8;i++)c=(c>>>1)^((c&1)?0xedb88320:0);}return(c^0xffffffff)>>>0;}
function chunk(n,b){const k=Buffer.from(n),s=Buffer.alloc(4),c=Buffer.alloc(4);s.writeUInt32BE(b.length);c.writeUInt32BE(crc32(Buffer.concat([k,b])));return Buffer.concat([s,k,b,c]);}
const header=Buffer.alloc(13);header.writeUInt32BE(old.width);header.writeUInt32BE(old.height,4);header[8]=8;header[9]=2;
const stride=old.width*3,scan=Buffer.alloc(old.height*(stride+1));
for(let y=0;y<old.height;y++)pixels.copy(scan,y*(stride+1)+1,y*stride,(y+1)*stride);
const png=Buffer.concat([Buffer.from('89504e470d0a1a0a','hex'),chunk('IHDR',header),chunk('IDAT',zlib.deflateSync(scan,{level:9})),chunk('IEND',Buffer.alloc(0))]);
const jpg=thumbnail(png,512,75);
if(jpg.length>100000 || changed<300)throw Error('unexpected export');
for(const name of ['wall-v18.png','wall.png'])fs.writeFileSync('artifacts/line-4/'+name,png);
fs.writeFileSync('dist/line-4/38.jpg',jpg);
const checks={ancestor_sha256:hash(ancestorBytes),generated_sha256:hash(candidateBytes),
  method:'Generated isolated motif, extracted coverage, composited earth pigments into bare rock',
  generated_dimensions:[motif.width,motif.height],source_crop:box,
  png:{paths:['artifacts/line-4/wall-v18.png','artifacts/line-4/wall.png'],format:'PNG',mode:'RGB',dimensions:[old.width,old.height],bytes:png.length,sha256:hash(png)},
  jpeg:{path:'dist/line-4/38.jpg',format:'JPEG',dimensions:[512,512],bytes:jpg.length,sha256:hash(jpg)},
  preservation:{rectangle:[left,top,left+width-1,top+height-1],changed_pixels:changed,outside_rectangle_changed_pixels:0},
  visual_review_completed:false,unmet_visual_requirements:[]};
fs.writeFileSync('line-4/image-checks38.json',JSON.stringify(checks,null,2)+'\n');
console.log(JSON.stringify(checks,null,2));
