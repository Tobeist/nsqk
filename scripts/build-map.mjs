import {readFile,writeFile} from 'node:fs/promises';
import {geoEquirectangular,geoPath,geoGraticule10} from 'd3';
import sharp from 'sharp';
const countries=JSON.parse(await readFile('public/assets/countries.geojson','utf8'));
const projection=geoEquirectangular().scale(2048/(2*Math.PI)).translate([1024,512]);
const path=geoPath(projection);
const shapes=countries.features.map(f=>{const active=['Mexico','United States of America'].includes(f.properties.ADMIN);return `<path d="${path(f)}" fill="${active?'#637f80':'#374f5a'}" stroke="${active?'#8caaaa':'#657e87'}" stroke-width="${active?'1.1':'.5'}"/>`;}).join('');
const svg=`<svg xmlns="http://www.w3.org/2000/svg" width="2048" height="1024"><defs><radialGradient id="ocean"><stop stop-color="#1b3b50"/><stop offset="1" stop-color="#102537"/></radialGradient><filter id="grain"><feTurbulence type="fractalNoise" baseFrequency=".025" numOctaves="4" seed="7"/><feColorMatrix type="saturate" values="0"/><feComponentTransfer><feFuncA type="linear" slope=".14"/></feComponentTransfer><feBlend in="SourceGraphic" mode="soft-light"/></filter></defs><path fill="url(#ocean)" d="M0 0h2048v1024H0z"/><g filter="url(#grain)">${shapes}</g><path d="${path(geoGraticule10())}" fill="none" stroke="#99b5c0" stroke-opacity=".14" stroke-width=".6"/></svg>`;
await writeFile('public/assets/earth-map.svg',svg);
await sharp(Buffer.from(svg)).png().toFile('public/assets/earth-map.png');
// Accessible static fallback, same real geography and region footprint.
const {geoOrthographic}=await import('d3');
const ortho=geoOrthographic().rotate([102,-27]).scale(244).translate([260,260]);
const op=geoPath(ortho);
await writeFile('public/assets/earth-fallback.svg',`<svg xmlns="http://www.w3.org/2000/svg" width="520" height="520" viewBox="0 0 520 520"><circle cx="260" cy="260" r="244" fill="#102537" stroke="#48697d"/>${countries.features.map(f=>`<path d="${op(f)||''}" fill="${['Mexico','United States of America'].includes(f.properties.ADMIN)?'#637f80':'#374f5a'}" stroke="#78919b" stroke-width=".5"/>`).join('')}<path d="${op(geoGraticule10())}" fill="none" stroke="#8ba8b6" opacity=".15" stroke-width=".5"/></svg>`);
