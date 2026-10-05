// Only anonymous public GitHub endpoints are queried. No token is read or sent.
import { mkdir, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';

const owner = 'markdsilva';
const api = 'https://api.github.com';
async function get(endpoint) {
  const response = await fetch(`${api}${endpoint}`, {
    headers: { Accept: 'application/vnd.github+json', 'User-Agent': 'markdsilva-public-profile' },
    signal: AbortSignal.timeout(20000),
  });
  if (!response.ok) throw new Error(`Public GitHub request failed: ${response.status} ${endpoint}`);
  return response.json();
}

const repos = [];
for (let page = 1; ; page++) {
  const batch = await get(`/users/${owner}/repos?type=owner&per_page=100&page=${page}`);
  if (!Array.isArray(batch)) throw new Error('Invalid public repository response');
  repos.push(...batch.filter(repo => repo.private === false && repo.owner.login.toLowerCase() === owner));
  if (batch.length < 100) break;
}

const languages = {};
for (const repo of repos) {
  const bytes = await get(`/repos/${owner}/${encodeURIComponent(repo.name)}/languages`);
  for (const [language, count] of Object.entries(bytes)) {
    if (!Number.isFinite(count) || count < 0) throw new Error('Invalid language byte count');
    languages[language] = (languages[language] || 0) + count;
  }
}

const stars = repos.reduce((total, repo) => total + repo.stargazers_count, 0);
const primary = new Set(repos.map(repo => repo.language).filter(Boolean)).size;
const ranked = Object.entries(languages).sort((a, b) => b[1] - a[1]);
const total = ranked.reduce((sum, entry) => sum + entry[1], 0);
const top = ranked.slice(0, 3);
const remainder = ranked.slice(3).reduce((sum, entry) => sum + entry[1], 0);
if (remainder) top.push(['Other', remainder]);
const palette = { Python: '#c88a55', TypeScript: '#efb85c', CSS: '#e3cfab', Other: '#9b8b75' };
const xml = text => String(text).replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;');
const number = value => String(value).padStart(2, '0');
const date = new Intl.DateTimeFormat('en-GB', { day: '2-digit', month: 'short', year: 'numeric', timeZone: 'UTC' }).format(new Date());
const assets = fileURLToPath(new URL('../assets/', import.meta.url));
await mkdir(assets, { recursive: true });

for (const dark of [true, false]) {
  const c = dark
    ? { bg: '#191714', ink: '#faf6eb', muted: '#b8b0a2', line: '#3a332b', accent: '#efb85c' }
    : { bg: '#faf7f0', ink: '#25251f', muted: '#686252', line: '#ded6c8', accent: '#9c610f' };
  const metrics = [[repos.length, 'PUBLIC REPOSITORIES'], [primary, 'PRIMARY LANGUAGES'], [stars, 'REPOSITORY STARS']];
  let x = 40;
  const bar = top.map(([language, bytes]) => {
    const width = total ? bytes / total * 880 : 0;
    const shape = `<rect x="${x.toFixed(3)}" y="174" width="${width.toFixed(3)}" height="8" fill="${palette[language] || '#b7a385'}"/>`;
    x += width;
    return shape;
  }).join('');
  const legend = top.map(([language, bytes], index) => {
    const lx = 40 + index * 220;
    const percent = bytes / total * 100;
    const label = percent < 1 ? '&lt;1%' : `${Math.round(percent)}%`;
    return `<circle cx="${lx+4}" cy="205" r="4" fill="${palette[language] || '#b7a385'}"/><text x="${lx+17}" y="210" font-size="14" fill="${c.muted}">${xml(language)} <tspan fill="${c.ink}" font-weight="600">${label}</tspan></text>`;
  }).join('');
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="960" height="266" viewBox="0 0 960 266" role="img" aria-labelledby="title desc">
  <title id="title">Public GitHub stats for Mark Dsilva</title>
  <desc id="desc">${repos.length} public repositories, ${primary} primary languages, ${stars} repository stars. Repository language bytes include forks. Updated ${xml(date)}.</desc>
  <defs><clipPath id="bar"><rect x="40" y="174" width="880" height="8" rx="4"/></clipPath></defs>
  <rect x="0.5" y="0.5" width="959" height="265" rx="20" fill="${c.bg}" stroke="${c.line}"/>
  <g font-family="Segoe UI, Helvetica, Arial, sans-serif">
    ${metrics.map(([value, label], index) => `<text x="${40+index*310}" y="76" font-size="43" font-weight="650" letter-spacing="-1" fill="${index===0?c.accent:c.ink}">${number(value)}</text><text x="${40+index*310}" y="107" font-size="12" letter-spacing="1.2" fill="${c.muted}">${label}</text>`).join('')}
    <path d="M325 38V112M635 38V112M40 139H920" stroke="${c.line}"/>
    <g clip-path="url(#bar)">${bar}</g>
    ${legend || `<text x="40" y="210" font-size="14" fill="${c.muted}">No public language data yet.</text>`}
    <text x="40" y="245" font-size="11" letter-spacing="0.2" fill="${c.muted}">PUBLIC REPOSITORIES, INCLUDING FORKS</text>
    <text x="920" y="245" text-anchor="end" font-size="11" fill="${c.muted}">Updated ${xml(date)}</text>
  </g>
</svg>\n`;
  await writeFile(`${assets}/stats-${dark ? 'dark' : 'light'}.svg`, svg);
  let mx = 24;
  const mobileBar = top.map(([language, bytes]) => {
    const width = total ? bytes / total * 432 : 0;
    const shape = `<rect x="${mx.toFixed(3)}" y="140" width="${width.toFixed(3)}" height="8" fill="${palette[language] || '#b7a385'}"/>`;
    mx += width;
    return shape;
  }).join('');
  const mobileLegend = top.map(([language, bytes], index) => {
    const lx = 24 + (index % 2) * 224;
    const ly = 177 + Math.floor(index / 2) * 28;
    const percent = bytes / total * 100;
    const label = percent < 1 ? '&lt;1%' : `${Math.round(percent)}%`;
    return `<circle cx="${lx+4}" cy="${ly-5}" r="4" fill="${palette[language] || '#b7a385'}"/><text x="${lx+17}" y="${ly}" font-size="14" fill="${c.muted}">${xml(language)} <tspan fill="${c.ink}" font-weight="600">${label}</tspan></text>`;
  }).join('');
  const mobileSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="480" height="268" viewBox="0 0 480 268" role="img" aria-labelledby="title desc">
  <title id="title">Public GitHub stats for Mark Dsilva</title>
  <desc id="desc">${repos.length} public repositories, ${primary} primary languages, ${stars} repository stars. Includes forks. Updated ${xml(date)}.</desc>
  <defs><clipPath id="bar"><rect x="24" y="140" width="432" height="8" rx="4"/></clipPath></defs>
  <rect x="0.5" y="0.5" width="479" height="267" rx="20" fill="${c.bg}" stroke="${c.line}"/>
  <g font-family="Segoe UI, Helvetica, Arial, sans-serif">
    ${[[repos.length,'Public repos'],[primary,'Main languages'],[stars,'Repo stars']].map(([value,label],index) => `<text x="${24+index*148}" y="63" font-size="35" font-weight="650" fill="${index===0?c.accent:c.ink}">${number(value)}</text><text x="${24+index*148}" y="89" font-size="12" fill="${c.muted}">${label}</text>`).join('')}
    <path d="M156 28V94M304 28V94M24 115H456" stroke="${c.line}"/>
    <g clip-path="url(#bar)">${mobileBar}</g>
    ${mobileLegend}
    <text x="24" y="238" font-size="11" fill="${c.muted}">Public repositories, including forks</text>
    <text x="24" y="255" font-size="11" fill="${c.muted}">Updated ${xml(date)}</text>
  </g>
</svg>\n`;
  await writeFile(`${assets}/stats-mobile-${dark ? 'dark' : 'light'}.svg`, mobileSvg);
}
console.log(`Updated public stats: ${repos.length} repositories, ${primary} primary languages, ${stars} stars.`);
