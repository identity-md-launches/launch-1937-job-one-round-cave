// Isolate the new pigment from the image tool's output onto the verified wall.
// Usage: node gathering/finish_wall38.js GENERATED_PNG
'use strict';
const fs = require('node:fs');
const zlib = require('node:zlib');
const crypto = require('node:crypto');
const {decode, thumbnail} = require('./thumbnail.js');

const ancestorBytes = fs.readFileSync('artifacts/gathering/wall-v17.png');
const ancestorHash = '0f4d55a16bccf29be5f82d92892c7cb062a9be4f9c3836c6f0619a7eff67fad8';
if (crypto.createHash('sha256').update(ancestorBytes).digest('hex') !== ancestorHash)
  throw new Error('expected the verified Gathering 37 ancestor');
const freshBytes = fs.readFileSync(process.argv[2]);
const old = decode(ancestorBytes), fresh = decode(freshBytes);
if (old.width !== 1254 || old.height !== 1254 || old.channels !== 3 ||
    fresh.width !== old.width || fresh.height !== old.height || fresh.channels < 3)
  throw new Error('image dimensions or format changed');

// The image tool painted a pair of cups and three chalk pebbles in this previously bare patch.
// Admit pigment-colored changes and a 2-pixel soft edge; discard its repaint of
// the inherited wall everywhere else.
const box = [485, 1100, 760, 1165];
const width = old.width, height = old.height;
const mask = new Uint8Array(width * height);
for (let y = box[1]; y <= box[3]; y++) for (let x = box[0]; x <= box[2]; x++) {
  const p = (y * width + x) * 3;
  const [r,g,b] = fresh.pixels.subarray(p,p+3);
  const [or,og,ob] = old.pixels.subarray(p,p+3);
  const dark = r < 150 && g < 110 && b < 85 && or-r > 10 && og-g > 7;
  const ochre = r > g*1.35 && g > b*1.7 && b < 37 && ob-b > 9;
  const chalk = r > 130 && g > 100 && b > 65 && b-ob > 15 && g-og > 5;
  if (dark || ochre || chalk) mask[y*width+x] = 1;
}
const out = Buffer.from(old.pixels);
let changed = 0, changedBox = [width,height,-1,-1];
for (let y=box[1]; y<=box[3]; y++) for(let x=box[0]; x<=box[2]; x++) {
  let distance=3;
  for(let dy=-2;dy<=2;dy++)for(let dx=-2;dx<=2;dx++) {
    if(x+dx < box[0] || x+dx > box[2] || y+dy < box[1] || y+dy > box[3])continue;
    if(mask[(y+dy)*width+x+dx])distance=Math.min(distance,Math.max(Math.abs(dx),Math.abs(dy)));
  }
  if(distance>2)continue;
  const edge=Math.min(x-box[0],box[2]-x,y-box[1],box[3]-y);
  const alpha=Math.min(1,edge/4)*(distance===0?.9:distance===1?.38:.14);
  const p=(y*width+x)*3;
  for(let c=0;c<3;c++)out[p+c]=Math.round(old.pixels[p+c]*(1-alpha)+fresh.pixels[p+c]*alpha);
  if(out[p]!==old.pixels[p]||out[p+1]!==old.pixels[p+1]||out[p+2]!==old.pixels[p+2]) {
    changed++;changedBox=[Math.min(changedBox[0],x),Math.min(changedBox[1],y),
                          Math.max(changedBox[2],x),Math.max(changedBox[3],y)];
  }
}
if(changed<300||changed>12000)throw new Error('unexpected pigment pixel count '+changed);
function crc32(bytes) {
  let crc=0xffffffff;
  for(const v of bytes){crc^=v;for(let b=0;b<8;b++)crc=(crc>>>1)^((crc&1)?0xedb88320:0);}
  return (crc^0xffffffff)>>>0;
}
function chunk(name,data) {
  const kind=Buffer.from(name),length=Buffer.alloc(4),crc=Buffer.alloc(4);
  length.writeUInt32BE(data.length);crc.writeUInt32BE(crc32(Buffer.concat([kind,data])));
  return Buffer.concat([length,kind,data,crc]);
}
const ihdr=Buffer.alloc(13);
ihdr.writeUInt32BE(width);ihdr.writeUInt32BE(height,4);ihdr[8]=8;ihdr[9]=2;
const stride=width*3,scan=Buffer.alloc(height*(stride+1));
for(let y=0;y<height;y++)out.copy(scan,y*(stride+1)+1,y*stride,(y+1)*stride);
const png=Buffer.concat([Buffer.from('89504e470d0a1a0a','hex'),chunk('IHDR',ihdr),
  chunk('IDAT',zlib.deflateSync(scan,{level:9})),chunk('IEND',Buffer.alloc(0))]);
fs.writeFileSync('artifacts/gathering/wall-v18.png',png);
fs.writeFileSync('artifacts/gathering/wall.png',png);
const jpeg=thumbnail(png,512,75);
if(jpeg.length>=100000)throw new Error('JPEG exceeds 100 KB');
fs.writeFileSync('dist/gathering/38.jpg',jpeg);
const result={ancestor_sha256:ancestorHash,
  generated_sha256:crypto.createHash('sha256').update(freshBytes).digest('hex'),
  png:{path:'artifacts/gathering/wall-v18.png',format:'PNG',mode:'RGB',dimensions:[width,height],
    bytes:png.length,sha256:crypto.createHash('sha256').update(png).digest('hex')},
  jpeg:{path:'dist/gathering/38.jpg',format:'JPEG',dimensions:[512,512],bytes:jpeg.length},
  preservation:{rectangle:box,changed_pixels:changed,changed_bounds:changedBox,
                outside_rectangle_changed_pixels:0},
  model:'built-in image_gen; pigment isolated over verified ancestor',
  visual_review_completed:false,unmet_visual_requirements:[]};
fs.writeFileSync('gathering/image-checks38.json',JSON.stringify(result,null,2)+'\n');
console.log(JSON.stringify(result,null,2));
