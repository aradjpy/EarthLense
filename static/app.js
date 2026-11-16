/* EarthLense frontend JavaScript: developed with AI assistance (OpenAI ChatGPT); data calculations run on the Python backend. */
const $ = (id) => document.getElementById(id);

const locations = {
  toronto: { name: 'Toronto, Canada', latitude: 43.7, longitude: -79.4 },
  newyork: { name: 'New York, USA', latitude: 40.7128, longitude: -74.006 },
  london: { name: 'London, UK', latitude: 51.5072, longitude: -0.1276 },
  cairo: { name: 'Cairo, Egypt', latitude: 30.0444, longitude: 31.2357 },
  sydney: { name: 'Sydney, Australia', latitude: -33.8688, longitude: 151.2093 },
  delhi: { name: 'New Delhi, India', latitude: 28.6139, longitude: 77.209 }
};

const atmosphericVariables = { clouds: 'CLOUD_AMT', aerosols: 'AOD_55' };
let selectedAtmosphere = 'clouds';

let currentData = null;
let currentMode = 'annual';
let currentLocation = 'Toronto, Canada';

const withSign = (number, digits = 2) => `${number > 0 ? '+' : ''}${Number(number).toFixed(digits)}`;
const showP = (number) => number < 0.0001 ? '< 0.0001' : Number(number).toFixed(4);

function setMessage(message = '') {
  $('form-message').textContent = message;
  $('form-message').hidden = !message;
}

function setBusy(isBusy) {
  $('analyze-button').disabled = isBusy;
  $('demo-button').disabled = isBusy;
  $('analyze-button-text').textContent = isBusy ? '🛰️ Asking NASA for clues…' : '✨ Discover what changed';
  $('analyze-button').setAttribute('aria-busy', String(isBusy));
}

function choosePreset() {
  const selected = $('preset-location').value;
  const location = locations[selected];
  if (location) {
    $('latitude').value = location.latitude.toFixed(4);
    $('longitude').value = location.longitude.toFixed(4);
  }
  $('advanced-location').open = selected === 'custom';
  setMessage();
}

function useCustomLocation() {
  const selected = locations[$('preset-location').value];
  if (!selected || Number($('latitude').value) !== selected.latitude || Number($('longitude').value) !== selected.longitude) {
    $('preset-location').value = 'custom';
    $('advanced-location').open = true;
  }
}

function useMyLocation() {
  const feedback = $('location-feedback');
  feedback.hidden = false;
  if (!navigator.geolocation) {
    feedback.textContent = 'Your browser cannot share your location. You can still choose a city or enter coordinates.';
    return;
  }
  feedback.textContent = 'Your browser may ask permission. We only use an approximate spot for this search.';
  $('locate-button').disabled = true;
  navigator.geolocation.getCurrentPosition((position) => {
    // Round to approximately one-kilometer precision; no street address is needed.
    $('latitude').value = position.coords.latitude.toFixed(2);
    $('longitude').value = position.coords.longitude.toFixed(2);
    $('preset-location').value = 'custom';
    $('advanced-location').open = true;
    feedback.textContent = 'Location ready! Your coordinates were rounded for privacy. Press Discover to see what NASA found.';
    $('locate-button').disabled = false;
    setMessage();
  }, () => {
    feedback.textContent = 'Could not get your location. Try selecting a city or entering coordinates instead.';
    $('locate-button').disabled = false;
  }, {enableHighAccuracy: false, timeout: 9000, maximumAge: 600000});
}

function selectedVariable() {
  return document.querySelector('input[name="variable"]:checked')?.value;
}

function validateInputs() {
  const latitude = Number($('latitude').value);
  const longitude = Number($('longitude').value);
  const start_year = Number($('start-year').value);
  const end_year = Number($('end-year').value);
  const variable = selectedVariable();

  if (!$('latitude').value || !$('longitude').value || !Number.isFinite(latitude) || !Number.isFinite(longitude) || latitude < -90 || latitude > 90 || longitude < -180 || longitude > 180) {
    throw new Error('We need a real spot on Earth! Latitude is −90 to 90, and longitude is −180 to 180.');
  }
  if (!$('start-year').value || !$('end-year').value || !Number.isInteger(start_year) || !Number.isInteger(end_year) || start_year < 1981 || end_year > new Date().getFullYear() - 1 || end_year - start_year + 1 < 10) {
    throw new Error('Pick at least 10 complete years, starting in 1981 or later.');
  }
  if (!variable) throw new Error('Choose a valid Earth clue.');
  if (['CLOUD_AMT','AOD_55'].includes(variable) && start_year < 2001) {
    throw new Error('Cloud and aerosol measurements start in 2001. Choose a later start year.');
  }
  return { latitude, longitude, start_year, end_year, variables: [variable] };
}

async function analyze(event) {
  event?.preventDefault();
  let input;
  try { input = validateInputs(); } catch (error) { setMessage(error.message); return; }
  setMessage();
  setBusy(true);
  try {
    const response = await fetch('/api/analyze', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(input)
    });
    const data = await response.json();
    if (!response.ok) {
      const detail = Array.isArray(data.detail) ? data.detail.map(item => item.msg).join(', ') : data.detail;
      throw new Error(detail || `NASA's data could not be read (HTTP ${response.status}).`);
    }
    const name = locations[$('preset-location').value]?.name || 'Your chosen spot';
    display(data, name);
  } catch (error) {
    setMessage(`We couldn't finish that search: ${error.message}. You can still try the saved Toronto example!`);
  } finally { setBusy(false); }
}

async function loadDemo() {
  setMessage();
  setBusy(true);
  try {
    const response = await fetch('/api/demo');
    if (!response.ok) throw new Error('The saved example is unavailable.');
    const data = await response.json();
    $('preset-location').value = 'toronto';
    choosePreset();
    $('start-year').value = '2001';
    $('end-year').value = '2024';
    document.querySelector('input[name="variable"][value="T2M"]').checked = true;
    display(data, locations.toronto.name);
  } catch (error) { setMessage(error.message); }
  finally { setBusy(false); }
}

function display(data, locationName) {
  currentData = data;
  currentLocation = locationName;
  const { trend, story, period, variable, data_source } = data;
  const unit = variable.unit === 'unitless' ? 'AOD' : variable.unit;
  const significant = !!trend.statistically_significant_at_0_05;
  currentMode = 'annual';
  updateModeButtons();

  // These short explanations come from the backend's storytelling layer.
  $('result-title').textContent = locationName;
  $('finding-title').textContent = story.headline;
  $('finding-description').textContent = story.description;
  $('story-emoji').textContent = story.emoji;
  $('result-subtitle').textContent = `${variable.name.replace(/^2 m /, '')} · ${period.start_year}–${period.end_year}`;
  $('retrieval-tag').textContent = data_source.retrieval === 'live' ? '🟢 FRESH NASA DATA' : data_source.retrieval === 'cache' ? '🗂️ CACHED NASA DATA' : '📚 SAVED NASA EXAMPLE';
  $('story-confidence').textContent = significant ? '✓ A clear long-term pattern' : '🔍 Still a mystery';
  $('story-confidence').classList.toggle('uncertain', !significant);

  $('metric-slope').textContent = `${withSign(trend.slope_per_decade)} ${unit}`;
  $('metric-slope-note').textContent = significant ? 'How much the trend line changes in 10 years' : 'Estimated slope — not a confirmed trend';
  $('metric-change').textContent = `${withSign(trend.estimated_change_over_period)} ${unit}`;
  $('metric-change-note').textContent = significant ? 'Estimated change from the long-term line' : 'Line estimate — the trend is uncertain';
  $('metric-evidence').textContent = story.evidence_label;
  $('metric-evidence-note').textContent = story.evidence_description;

  // Technical evidence stays available for teachers, scientists and judges.
  $('metric-pvalue').textContent = showP(trend.p_value);
  $('metric-r2').textContent = Number(trend.r_squared).toFixed(3);
  const ci = trend.slope_95pct_ci_per_decade;
  $('confidence-value').textContent = `${withSign(ci[0])} to ${withSign(ci[1])} ${unit} / 10 yrs`;
  $('science-interpretation').textContent = significant
    ? `The model's statistical test supports a nonzero trend. ${story.change_explanation}`
    : `The test doesn't provide enough evidence for a clear trend. ${story.change_explanation}`;
  $('chart-foot-years').textContent = `${trend.n_years} complete years · NASA POWER (${data_source.retrieval})`;
  $('export-button').disabled = false;
  renderChart();
}

function updateModeButtons() {
  for (const mode of ['annual', 'monthly']) {
    const active = currentMode === mode;
    const button = $(mode + '-button');
    button.classList.toggle('active', active);
    button.setAttribute('aria-pressed', String(active));
  }
}

const svgNS = 'http://www.w3.org/2000/svg';
function svgNode(tag, attrs = {}, content) {
  const node = document.createElementNS(svgNS, tag);
  Object.entries(attrs).forEach(([name, value]) => node.setAttribute(name, String(value)));
  if (content !== undefined) node.textContent = content;
  return node;
}

function renderChart() {
  if (!currentData) return;
  const monthly = currentMode === 'monthly';
  const points = monthly ? currentData.observed_monthly_series : currentData.observed_annual_series;
  const fitted = monthly ? [] : currentData.trend.fitted_annual_series;
  if (!points?.length) return;
  const { variable } = currentData;
  $('chart-title').textContent = `${monthly ? 'Month-by-month' : 'Year-by-year'} ${variable.name.replace(/^2 m /, '').toLowerCase()}`;
  $('chart-description').textContent = monthly
    ? 'This view shows how the readings rise and fall with the seasons.'
    : 'Each blue dot represents the average of one full year.';
  $('chart-explainer').textContent = monthly
    ? '💡 Seasons can make the line jump up and down. Switch to Yearly to look for the bigger, long-term pattern.'
    : '💡 One year can be different from the next. The orange line shows the long-term direction of the data.';
  $('fitted-legend').hidden = monthly;

  const svg = $('trend-chart');
  svg.replaceChildren();
  const W = 960, H = 350, left = 62, right = 20, top = 19, bottom = 37;
  const plotW = W - left - right, plotH = H - top - bottom;
  const series = points.map(p => Number(p.value));
  const fittedSeries = fitted.map(p => Number(p.value));
  let low = Math.min(...series, ...fittedSeries);
  let high = Math.max(...series, ...fittedSeries);
  const spread = Math.max(.01, high - low);
  low -= spread * .13;
  high += spread * .13;
  const atX = (i) => left + i / Math.max(1,points.length - 1) * plotW;
  const atY = (v) => top + (high - v) / (high - low) * plotH;
  const fmt = (v) => Math.abs(v) >= 100 ? v.toFixed(0) : v.toFixed(1);

  const defs = svgNode('defs');
  const gradient = svgNode('linearGradient', { id:'earthChartFill',x1:0,x2:0,y1:0,y2:1 });
  gradient.append(svgNode('stop', { offset:'0%','stop-color':'#679ef3','stop-opacity':'.23' }), svgNode('stop', { offset:'100%','stop-color':'#679ef3','stop-opacity':'0' }));
  defs.append(gradient);
  svg.append(defs);

  for (let i = 0; i <= 5; i++) {
    const value = low + i * (high - low) / 5;
    const y = atY(value);
    svg.append(svgNode('line', { x1:left, y1:y, x2:W-right, y2:y, stroke:'#e5edf5','stroke-width':1,'stroke-dasharray':i ? '4 5' : '0' }));
    svg.append(svgNode('text', { x:left-10,y:y+4,'text-anchor':'end' }, fmt(value)));
  }
  for (let i = 0; i < Math.min(6, points.length); i++) {
    const index = Math.round(i * (points.length - 1) / Math.max(1,Math.min(6,points.length)-1));
    const label = monthly ? points[index].date.slice(0,4) : points[index].year;
    svg.append(svgNode('text', {x:atX(index),y:H-8,'text-anchor':i===0?'start':i===Math.min(6,points.length)-1?'end':'middle'}, label));
  }

  const plotPath = series.map((v,i) => `${i===0?'M':'L'} ${atX(i).toFixed(2)} ${atY(v).toFixed(2)}`).join(' ');
  const filledPath = `${plotPath} L ${atX(points.length-1)} ${atY(low)} L ${atX(0)} ${atY(low)} Z`;
  svg.append(svgNode('path', {d:filledPath,fill:'url(#earthChartFill)'}));
  svg.append(svgNode('path', {d:plotPath,fill:'none',stroke:'#4c85e5','stroke-width':monthly?2.4:3,'stroke-linejoin':'round','stroke-linecap':'round'}));
  if (!monthly) {
    const fitPath = fittedSeries.map((v,i) => `${i===0?'M':'L'} ${atX(i).toFixed(2)} ${atY(v).toFixed(2)}`).join(' ');
    svg.append(svgNode('path', {d:fitPath,fill:'none',stroke:'#f09d4c','stroke-width':3.3,'stroke-dasharray':'9 6','stroke-linecap':'round'}));
    series.forEach((v,i) => svg.append(svgNode('circle', {cx:atX(i),cy:atY(v),r:3.5,fill:'#4d87e6',stroke:'#fff','stroke-width':1.7})));
  }

  const hoverLine = svgNode('line', {y1:top,y2:H-bottom,stroke:'#8fa4bf','stroke-dasharray':'4 5','stroke-width':1,opacity:0});
  const hoverDot = svgNode('circle', {r:5.5,fill:'#fff',stroke:'#3671d5','stroke-width':2,opacity:0});
  const hit = svgNode('rect', {x:left,y:top,width:plotW,height:plotH,fill:'transparent','pointer-events':'all'});
  svg.append(hoverLine,hoverDot,hit);
  const tooltip = $('chart-tooltip');
  hit.addEventListener('pointermove', (event) => {
    const rect = svg.getBoundingClientRect();
    const svgX = (event.clientX - rect.left) / rect.width * W;
    const index = Math.max(0,Math.min(points.length-1,Math.round((svgX-left)/plotW*(points.length-1))));
    const x = atX(index), y = atY(series[index]);
    hoverLine.setAttribute('x1',x);hoverLine.setAttribute('x2',x);hoverLine.setAttribute('opacity','1');
    hoverDot.setAttribute('cx',x);hoverDot.setAttribute('cy',y);hoverDot.setAttribute('opacity','1');
    tooltip.textContent = `${monthly ? points[index].date : points[index].year}: ${series[index].toFixed(2)} ${variable.unit}`;
    tooltip.hidden = false;
    tooltip.style.left = `${Math.max(75,Math.min(rect.width-75,x/W*rect.width))}px`;
    tooltip.style.top = `${Math.max(30,y/H*rect.height-7)}px`;
  });
  hit.addEventListener('pointerleave', () => { hoverLine.setAttribute('opacity','0');hoverDot.setAttribute('opacity','0');tooltip.hidden=true; });
  svg.setAttribute('aria-label',`${monthly ? 'Monthly':'Annual'} NASA ${variable.name} in ${currentLocation}, ${currentData.period.start_year} to ${currentData.period.end_year}. ${series.length} observations.`);
}

function exportCSV() {
  if (!currentData) return;
  const {observed_annual_series,trend,variable,location,period} = currentData;
  const fittedByYear = new Map(trend.fitted_annual_series.map(p => [p.year,p.value]));
  const rows = [['year',`observed_${variable.id}`,`fitted_${variable.id}`]];
  observed_annual_series.forEach(p => rows.push([p.year,p.value,fittedByYear.get(p.year)]));
  const content = rows.map(row => row.join(',')).join('\r\n');
  const url = URL.createObjectURL(new Blob([content],{type:'text/csv;charset=utf-8'}));
  const link = document.createElement('a');
  link.href=url;
  link.download=`EarthLense_${variable.id}_${location.latitude}_${location.longitude}_${period.start_year}-${period.end_year}.csv`;
  document.body.append(link);link.click();link.remove();URL.revokeObjectURL(url);
}

function renderMiniChart(svg, series, fit, bounds = null, width = 160, height = 72) {
  svg.replaceChildren();
  const values = [...series, ...fit];
  if (!values.length) return;
  const min = bounds ? bounds.min : Math.min(...values);
  const max = bounds ? bounds.max : Math.max(...values);
  const range = Math.max(0.000001, max - min);
  const x = i => 8 + (i / Math.max(1, series.length - 1)) * (width - 16);
  const y = v => height - 9 - ((v - min) / range) * (height - 18);
  const path = values => values.map((v, i) => `${i ? 'L' : 'M'} ${x(i).toFixed(1)} ${y(v).toFixed(1)}`).join(' ');
  svg.append(svgNode('path', {d: path(series), fill:'none', stroke:'#4c85e5', 'stroke-width':2.6, 'stroke-linejoin':'round'}));
  svg.append(svgNode('path', {d: path(fit), fill:'none', stroke:'#ed913e', 'stroke-width':2.4, 'stroke-dasharray':'5 3'}));
  svg.hidden = false;
}

function renderComparisonCharts(a, b) {
  // Identical y-axis scale means the differences between locations remain visible.
  const numbers = [a,b].flatMap(result => [
    ...result.observed_annual_series.map(point => Number(point.value)),
    ...result.trend.fitted_annual_series.map(point => Number(point.value))
  ]);
  const bounds = {min: Math.min(...numbers), max: Math.max(...numbers)};
  for (const [id, result] of [['a',a],['b',b]]) {
    renderMiniChart($(`compare-${id}-chart`),
      result.observed_annual_series.map(p => Number(p.value)),
      result.trend.fitted_annual_series.map(p => Number(p.value)), bounds);
  }
}

function comparisonLocation(id) {
  const value = $(`compare-${id}`).value;
  if (value !== 'custom') return locations[value];
  const latInput = $(`compare-${id}-lat`);
  const lonInput = $(`compare-${id}-lon`);
  const latitude = Number(latInput.value);
  const longitude = Number(lonInput.value);
  if (!latInput.value || !lonInput.value || !Number.isFinite(latitude) || !Number.isFinite(longitude) || latitude < -90 || latitude > 90 || longitude < -180 || longitude > 180) {
    throw new Error(`Enter valid coordinates for Place ${id.toUpperCase()}.`);
  }
  return {name: `(${latitude.toFixed(2)}°, ${longitude.toFixed(2)}°)`, latitude, longitude};
}

function updateCompare() {
  for (const id of ['a','b']) {
    const custom = $(`compare-${id}`).value === 'custom';
    $(`compare-${id}-coordinates`).hidden = !custom;
    const location = custom ? null : locations[$(`compare-${id}`).value];
    $(`compare-${id}-name`).textContent = location?.name || 'Your custom place';
    $(`compare-${id}-result`).textContent = 'Press Compare to begin';
    $(`compare-${id}-chart`).hidden = true;
  }
}

async function comparePlaces() {
  const message = $('compare-message');
  const button = $('compare-button');
  let selection, locA, locB;
  try {
    selection = validateInputs();
    locA = comparisonLocation('a');
    locB = comparisonLocation('b');
  } catch (error) { message.textContent = error.message; return; }
  if (Math.abs(locA.latitude - locB.latitude) < 0.000001 && Math.abs(locA.longitude - locB.longitude) < 0.000001) {
    message.textContent = 'Choose two different places.'; return;
  }
  button.disabled = true;
  message.textContent = `🛰️ Fetching NASA measurements for ${locA.name} and ${locB.name}…`;
  try {
    const a = {...selection, latitude:locA.latitude, longitude:locA.longitude};
    const b = {...selection, latitude:locB.latitude, longitude:locB.longitude};
    const response = await fetch('/api/compare', {
      method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({location_a:a,location_b:b})
    });
    const results = await response.json();
    if (!response.ok) throw new Error(typeof results.detail === 'string' ? results.detail : 'Comparison unavailable. Please try again.');
    const unit = results.a.variable.unit === 'unitless' ? 'AOD' : results.a.variable.unit;
    $('compare-a-name').textContent = locA.name;
    $('compare-b-name').textContent = locB.name;
    $('compare-a-result').textContent = `${withSign(results.a.trend.slope_per_decade)} ${unit} / 10 years · ${results.a.story.evidence_label}`;
    $('compare-b-result').textContent = `${withSign(results.b.trend.slope_per_decade)} ${unit} / 10 years · ${results.b.story.evidence_label}`;
    renderComparisonCharts(results.a, results.b);
    const diff = Number(results.slope_difference_a_minus_b_per_decade);
    message.textContent = `${results.a.variable.name}, ${selection.start_year}–${selection.end_year}: ${locA.name} changed ${withSign(diff)} ${unit} per decade relative to ${locB.name}, based on fitted slopes. This does not test whether the difference is statistically significant. NASA retrievals: ${results.a.data_source.retrieval}, ${results.b.data_source.retrieval}.`;
  } catch (error) {
    message.textContent = 'Unable to compare right now: ' + error.message;
  } finally { button.disabled = false; }
}

async function investigateAtmosphere() {
  const message = $('atmosphere-message');
  const button = $('atmosphere-button');
  let selection;
  try { selection = validateInputs(); }
  catch (error) { message.textContent = error.message; return; }
  const variable = atmosphericVariables[selectedAtmosphere];
  selection.variables = [variable];
  if (selection.start_year < 2001) {
    message.textContent = 'NASA cloud/aerosol data begins in 2001. Set the starting year to 2001 or later.';
    return;
  }
  button.disabled = true;
  $('atmosphere-results').hidden = true;
  message.textContent = '🛰️ Looking up real NASA atmospheric data…';
  try {
    const response = await fetch('/api/analyze', {
      method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(selection)
    });
    const data = await response.json();
    if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Could not analyze the atmosphere.');
    const unit = data.variable.unit === 'unitless' ? 'AOD units' : data.variable.unit === '%' ? 'percentage points' : data.variable.unit;
    const locationName = locations[$('preset-location').value]?.name || 'Your chosen area';
    $('atmosphere-headline').textContent = `${data.story.emoji} ${data.story.headline}`;
    $('atmosphere-description').textContent = `${locationName}, ${data.period.start_year}–${data.period.end_year}. ${data.story.description}`;
    $('atmosphere-slope').textContent = `${withSign(data.trend.slope_per_decade)} ${unit}`;
    $('atmosphere-evidence').textContent = data.story.evidence_label;
    $('atmosphere-caveat').textContent = data.story.variable_explanation + ' ' + data.story.data_note;
    renderMiniChart($('atmosphere-chart'),
      data.observed_annual_series.map(p => Number(p.value)),
      data.trend.fitted_annual_series.map(p => Number(p.value)), null, 360, 125);
    $('atmosphere-results').hidden = false;
    message.textContent = `NASA POWER · CERES SYN1deg · ${data.data_source.retrieval} data. Blue: measurements · orange: fitted trend.`;
  } catch (error) {
    message.textContent = 'Could not load the atmospheric analysis: ' + error.message;
  } finally { button.disabled = false; }
}

function initializeExploration() {
  document.querySelectorAll('[data-atmosphere]').forEach(button => {
    button.addEventListener('click', () => {
      selectedAtmosphere = button.dataset.atmosphere;
      document.querySelectorAll('[data-atmosphere]').forEach(other => {
        const active = other === button;
        other.classList.toggle('active', active);
        other.setAttribute('aria-pressed', String(active));
      });
      $('atmosphere-results').hidden = true;
      $('atmosphere-message').textContent = `Ready to investigate ${selectedAtmosphere === 'clouds' ? 'cloud cover' : 'airborne particles'}. Press Investigate the atmosphere.`;
    });
  });
  $('atmosphere-button').addEventListener('click', investigateAtmosphere);
  for (const id of ['a','b']) {
    $(`compare-${id}`).addEventListener('change', updateCompare);
  }
  $('compare-button').addEventListener('click', comparePlaces);
  updateCompare();
}

async function initialize() {
  $('analysis-form').addEventListener('submit',analyze);
  $('preset-location').addEventListener('change',choosePreset);
  $('latitude').addEventListener('input',useCustomLocation);
  $('longitude').addEventListener('input',useCustomLocation);
  $('demo-button').addEventListener('click',loadDemo);
  $('locate-button').addEventListener('click',useMyLocation);
  $('export-button').addEventListener('click',exportCSV);
  for (const mode of ['annual','monthly']) {
    $(mode+'-button').addEventListener('click',() => {currentMode=mode;updateModeButtons();renderChart();});
  }
  initializeExploration();
  try {
    const response = await fetch('/api/variables');
    if (response.ok) {
      const variables = await response.json();
      document.querySelectorAll('input[name="variable"]').forEach(input => {
        const metadata = variables.find(v => v.id===input.value);
        input.disabled = !metadata?.available;
      });
    }
  } catch (_) { /* Keep static variable choices if metadata is temporarily unavailable. */ }
  await loadDemo();
}

document.addEventListener('DOMContentLoaded',initialize);
