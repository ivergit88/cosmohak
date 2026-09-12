/* Презентация защиты — КосмоХакатон 2026, кейс «Проектирование устойчивой спутниковой группировки».
   Сборка: node presentation/build_deck.js (из корня проекта). */
const path = require("path");
const globalRoot = "C:/Users/Administrator/AppData/Roaming/npm/node_modules";
const pptxgen = require(path.join(globalRoot, "pptxgenjs"));

const W = 13.33, H = 7.5, M = 0.6;
// Палитра «орбита»: глубокий космос + сигнальный янтарь
const BG_DARK = "0B1626", BG_LIGHT = "F4F7FA";
const PRIMARY = "14507E", PRIMARY_MID = "3B7AB8", PRIMARY_SOFT = "9FC0DC";
const ACCENT = "F2A007";
const TEXT_D = "16222E", TEXT_L = "EAF2F8", MUTED = "5B6B7C", MUTED_L = "8FA5B8";
const F = "Arial";

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";
pres.author = "Команда КосмоХакатона";
pres.title = "Устойчивая спутниковая группировка — защита решения";

const IMG = (f) => path.join(__dirname, "img", f);

// Мотив: орбита — дуга эллипса + спутник-точка в правом верхнем углу
function orbit(slide, dark) {
  const c = dark ? PRIMARY_MID : PRIMARY_SOFT;
  slide.addShape(pres.shapes.OVAL, {
    x: W - 2.6, y: -1.5, w: 3.4, h: 2.4, fill: { type: "none" },
    line: { color: c, width: 1.2, transparency: dark ? 30 : 10 }, rotate: 18,
  });
  slide.addShape(pres.shapes.OVAL, {
    x: W - 1.28, y: 0.42, w: 0.14, h: 0.14, fill: { color: ACCENT }, line: { type: "none" },
  });
}

function titleBar(slide, kicker, title, dark) {
  slide.addText(kicker.toUpperCase(), {
    x: M, y: 0.42, w: 10, h: 0.32, fontFace: F, fontSize: 12, bold: true,
    color: dark ? PRIMARY_SOFT : PRIMARY_MID, charSpacing: 3, margin: 0,
  });
  slide.addText(title, {
    x: M, y: 0.74, w: 10.6, h: 0.75, fontFace: F, fontSize: 30, bold: true,
    color: dark ? TEXT_L : TEXT_D, margin: 0,
  });
}

function srcLine(slide, text, dark) {
  slide.addText(text, {
    x: M, y: H - 0.42, w: 12, h: 0.3, fontFace: F, fontSize: 11,
    color: dark ? MUTED_L : MUTED, margin: 0,
  });
}

// ---------------------------------------------------------------- 1. Титул
let s = pres.addSlide();
s.background = { color: BG_DARK };
s.addShape(pres.shapes.OVAL, { x: 7.4, y: -3.4, w: 9.5, h: 9.5, fill: { type: "none" }, line: { color: PRIMARY_MID, width: 1.4, transparency: 35 } });
s.addShape(pres.shapes.OVAL, { x: 8.9, y: -1.9, w: 6.5, h: 6.5, fill: { type: "none" }, line: { color: PRIMARY_MID, width: 1.1, transparency: 55 } });
s.addShape(pres.shapes.OVAL, { x: 10.62, y: 1.62, w: 0.2, h: 0.2, fill: { color: ACCENT }, line: { type: "none" } });
s.addShape(pres.shapes.OVAL, { x: 8.05, y: 5.1, w: 0.13, h: 0.13, fill: { color: PRIMARY_SOFT }, line: { type: "none" } });
s.addText("КОСМОХАКАТОН 2026 · КЕЙС «ПРОЕКТИРОВАНИЕ УСТОЙЧИВОЙ СПУТНИКОВОЙ ГРУППИРОВКИ»", {
  x: M, y: 1.15, w: 11, h: 0.35, fontFace: F, fontSize: 13, bold: true, color: PRIMARY_SOFT, charSpacing: 2, margin: 0,
});
s.addText("Веб-сервис проектирования\nи оценки доступности связи", {
  x: M, y: 1.7, w: 11.2, h: 2.1, fontFace: F, fontSize: 44, bold: true, color: TEXT_L, margin: 0, lineSpacing: 52,
});
s.addText([
  { text: "48 спутников · 550 км · 3 очереди запуска", options: { breakLine: true } },
  { text: "Цель кейса: доступность связи ≥ 90% расчётного времени для каждого северного пункта", options: {} },
], { x: M, y: 4.05, w: 9.6, h: 0.95, fontFace: F, fontSize: 17, color: MUTED_L, margin: 0, paraSpaceAfter: 6 });
s.addShape(pres.shapes.LINE, { x: M, y: 5.5, w: 3.2, h: 0, line: { color: ACCENT, width: 2.5 } });
s.addText([
  { text: "github.com/ivergit88/cosmohak   ·   streamlit run app.py   ·   docker", options: { breakLine: true } },
  { text: "Официальный geometry.py — в основе расчётов · 83 автотеста", options: {} },
], { x: M, y: 5.72, w: 10.5, h: 0.8, fontFace: F, fontSize: 13, color: PRIMARY_SOFT, margin: 0, paraSpaceAfter: 4 });

// ------------------------------------------------- 2. Задача и проблема
s = pres.addSlide();
s.background = { color: BG_LIGHT };
orbit(s, false);
titleBar(s, "Задача", "Видимость спутника ≠ доставка до шлюза");
const stats = [
  { n: "48", t: "спутников на орбите 550 км,\nзапуск в 3 очереди по 16" },
  { n: "720", t: "отсчётов расчётной сетки:\nсутки с шагом 120 секунд" },
  { n: "≥90%", t: "целевая доступность\nдля каждого из пунктов" },
];
stats.forEach((it, i) => {
  s.addText(it.n, { x: M + i * 4.15, y: 1.75, w: 3.7, h: 1.15, fontFace: F, fontSize: 60, bold: true, color: i === 2 ? ACCENT : PRIMARY, margin: 0 });
  s.addText(it.t, { x: M + i * 4.15, y: 2.95, w: 3.7, h: 0.75, fontFace: F, fontSize: 13, color: MUTED, margin: 0 });
});
s.addShape(pres.shapes.LINE, { x: M, y: 4.0, w: W - 2 * M, h: 0, line: { color: PRIMARY_SOFT, width: 1 } });
s.addText("Что ломает связь — и что должен показывать сервис", { x: M, y: 4.2, w: 12, h: 0.4, fontFace: F, fontSize: 16, bold: true, color: TEXT_D, margin: 0 });
const probs = [
  "Маршрут «пункт → спутники → шлюз» рвётся при движении аппаратов — даже когда спутник виден",
  "Один отказ затрагивает сразу несколько направлений; на ранних очередях развёртывания всё хуже",
  "Инженеру нужно сравнивать конфигурации на одном периоде и объяснять перерывы",
];
s.addText(probs.map((t, i) => ({ text: t, options: { bullet: { code: "25B8", indent: 12 }, breakLine: i < probs.length - 1 } })), {
  x: M, y: 4.65, w: 12.1, h: 2.2, fontFace: F, fontSize: 16, color: TEXT_D, paraSpaceAfter: 10, margin: 0,
});
srcLine(s, "Источник: «Постановка задачи» и «Описание данных», КосмоХакатон 2026", false);

// ------------------------------------- 3. Что делает сервис (процесс)
s = pres.addSlide();
s.background = { color: BG_LIGHT };
orbit(s, false);
titleBar(s, "Решение", "Полный цикл инженера в одном сервисе");
const steps = [
  ["1", "Загрузка сценария", "JSON cosmo-A-1.0; валидация\nс понятными ошибками"],
  ["2", "Конфигурация", "этап развёртывания, RAAN\nи фазирование, отказы"],
  ["3", "Расчёт сети", "720 отсчётов: позиции,\nвидимость, связи, ~0.5 с"],
  ["4", "Маршруты", "клиент → спутники → шлюз;\nпричина каждого перерыва"],
  ["5", "Сравнение", "варианты A/B, критичность,\nрекомендация с цифрами"],
  ["6", "Экспорт", "result JSON (2160 маршрутов),\nscenario, CSV — реимпорт"],
];
steps.forEach((st, i) => {
  const x = M + i * 2.07;
  s.addShape(pres.shapes.OVAL, { x: x, y: 1.95, w: 0.52, h: 0.52, fill: { color: i === 5 ? ACCENT : PRIMARY }, line: { type: "none" } });
  s.addText(st[0], { x: x, y: 1.95, w: 0.52, h: 0.52, fontFace: F, fontSize: 18, bold: true, color: "FFFFFF", align: "center", valign: "middle", margin: 0 });
  if (i < 5) s.addShape(pres.shapes.LINE, { x: x + 0.62, y: 2.21, w: 1.32, h: 0, line: { color: PRIMARY_SOFT, width: 1.5 } });
  s.addText(st[1], { x: x - 0.12, y: 2.65, w: 2.0, h: 0.55, fontFace: F, fontSize: 15, bold: true, color: TEXT_D, margin: 0 });
  s.addText(st[2], { x: x - 0.12, y: 3.2, w: 2.0, h: 1.1, fontFace: F, fontSize: 11.5, color: MUTED, margin: 0 });
});
s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: M, y: 4.75, w: W - 2 * M, h: 1.85, fill: { color: "FFFFFF" }, line: { type: "none" }, rectRadius: 0.08, shadow: { type: "outer", color: "1B2A3A", blur: 8, offset: 2, angle: 90, opacity: 0.14 } });
s.addText([
  { text: "Скрытый сценарий жюри — без правок кода. ", options: { bold: true, color: TEXT_D } },
  { text: "Ни один ID и ни одно число не захардкожены: состав, плоскости и параметры целиком читаются из файла. Валидация покрывает схему, диапазоны, типы и ссылки, указывая проблемное поле, — 44 граничных кейса в тестах; официальная geometry.validate — финальный рубеж.", options: { color: MUTED } },
], { x: M + 0.35, y: 5.0, w: 11.4, h: 1.35, fontFace: F, fontSize: 16, margin: 0 });

// ------------------------------- 4. Расчётная модель и маршрутизация
s = pres.addSlide();
s.background = { color: BG_LIGHT };
orbit(s, false);
titleBar(s, "Как считаем", "Официальная модель + детерминизм маршрутов");
s.addImage({ path: IMG("ui_3d.png"), x: 6.7, y: 1.75, w: 6.03, h: 3.77, sizing: { type: "cover", w: 6.03, h: 3.77 } });
s.addText("3D-сцена сервиса: Земля, 48 аппаратов, связи и маршрут в выбранный момент", { x: 6.7, y: 5.6, w: 6.03, h: 0.5, fontFace: F, fontSize: 11.5, color: MUTED, margin: 0 });
const algo = [
  ["Геометрия — только официальная", "координаты, видимость и связи из geometry.py организаторов; parity-тесты подтверждают совпадение с формулами «Описания данных»"],
  ["Сетка и отказы — по документу", "720 отсчётов (правый конец не включается), интервалы [start; end)"],
  ["RAAN/фаза — проектные параметры", "задаются до развёртывания; сравниваем конфигурации, а не «управляем спутником в полёте»"],
  ["Маршрут — Dijkstra по длине линий связи", "минимум суммарной геометрической длины на графе текущего отсчёта; tie-break детерминирован; наземные узлы не ретранслируют"],
  ["Каждый перерыв имеет причину", "нет видимого спутника · шлюз в отказе · нет контакта шлюза · разрыв межспутниковой сети"],
];
algo.forEach((it, i) => {
  const y = 1.78 + i * 1.05;
  s.addShape(pres.shapes.OVAL, { x: M, y: y + 0.06, w: 0.14, h: 0.14, fill: { color: i === 2 ? ACCENT : PRIMARY }, line: { type: "none" } });
  s.addText(it[0], { x: M + 0.32, y: y - 0.08, w: 5.5, h: 0.4, fontFace: F, fontSize: 15.5, bold: true, color: TEXT_D, margin: 0 });
  s.addText(it[1], { x: M + 0.32, y: y + 0.32, w: 5.55, h: 0.75, fontFace: F, fontSize: 12, color: MUTED, margin: 0 });
});
srcLine(s, "Расчётный модуль geometry.py предоставлен организаторами; маршрутизация, аналитика и интерфейс — работа команды", false);

// ------------------------------------------- 5. Результаты 4 сценариев
s = pres.addSlide();
s.background = { color: BG_LIGHT };
orbit(s, false);
titleBar(s, "Результаты", "Четыре сценария: от идеала до стресс-тестов");
s.addChart([
  {
    type: pres.charts.BAR,
    data: [
      { name: "C65", labels: ["Полная\nгруппировка", "1-я очередь", "10 отказов", "МСC 2000 км"], values: [96.67, 27.22, 79.31, 77.5] },
      { name: "C70", labels: ["Полная\nгруппировка", "1-я очередь", "10 отказов", "МСC 2000 км"], values: [98.75, 15.83, 80.83, 62.22] },
      { name: "C72", labels: ["Полная\nгруппировка", "1-я очередь", "10 отказов", "МСC 2000 км"], values: [98.89, 12.64, 82.5, 65.14] },
    ],
    options: { chartColors: [PRIMARY, PRIMARY_MID, ACCENT], barDir: "col", barGapWidthPct: 60 },
  },
  {
    type: pres.charts.LINE,
    data: [{ name: "Цель 90%", labels: ["Полная\nгруппировка", "1-я очередь", "10 отказов", "МСC 2000 км"], values: [90, 90, 90, 90] }],
    options: { chartColors: ["C62828"], lineSize: 2, lineDash: "dash", lineDataSymbol: "none" },
  },
], {
  x: M, y: 1.7, w: 7.6, h: 4.9,
  chartArea: { fill: { color: BG_LIGHT } },
  catAxisLabelColor: MUTED, valAxisLabelColor: MUTED, catAxisLabelFontSize: 11, valAxisLabelFontSize: 11,
  valAxisMaxVal: 100, valAxisMinVal: 0,
  valGridLine: { color: "DFE7EE", size: 0.5 }, catGridLine: { style: "none" },
  showLegend: true, legendPos: "b", legendColor: MUTED, legendFontSize: 11,
  showTitle: false, fontFace: F,
});
const outage = [
  ["Полная группировка", "96.7–98.9%", "2–8 мин"],
  ["1-я очередь", "12.6–27.2%", "до 13.3 ч"],
  ["10 отказов", "79.3–82.5%", "20–24 мин"],
  ["МСC 2000 км", "62.2–77.5%", "4 мин–3 ч"],
];
s.addText("Доступность и худший перерыв", { x: 8.6, y: 1.75, w: 4.2, h: 0.4, fontFace: F, fontSize: 15, bold: true, color: TEXT_D, margin: 0 });
outage.forEach((r, i) => {
  const y = 2.25 + i * 1.02;
  s.addText(r[0], { x: 8.6, y: y, w: 4.2, h: 0.3, fontFace: F, fontSize: 13, bold: true, color: TEXT_D, margin: 0 });
  s.addText([
    { text: r[1], options: { bold: true, color: i === 0 ? "2E7D32" : i === 1 ? "C62828" : PRIMARY } },
    { text: "  доступность ·  перерыв " + r[2], options: { color: MUTED } },
  ], { x: 8.6, y: y + 0.3, w: 4.2, h: 0.32, fontFace: F, fontSize: 12, margin: 0 });
  if (i < 3) s.addShape(pres.shapes.LINE, { x: 8.6, y: y + 0.78, w: 4.1, h: 0, line: { color: "DFE7EE", width: 1 } });
});
srcLine(s, "Расчёт команды: официальный geometry.py, сетка 720 отсчётов, стратегия мин. переходов; числа зафиксированы регрессионными тестами", false);

// ------------------------------------------- 6. Анализ устойчивости
s = pres.addSlide();
s.background = { color: BG_LIGHT };
orbit(s, false);
titleBar(s, "Устойчивость", "Отказы: кто ломает сеть и почему");
s.addText("S44", { x: M, y: 1.85, w: 3.4, h: 1.3, fontFace: F, fontSize: 66, bold: true, color: ACCENT, margin: 0 });
s.addText("самый критичный аппарат полной группировки: его виртуальный отказ сильнее всего роняет минимальную доступность по пунктам", {
  x: M, y: 3.15, w: 3.7, h: 1.5, fontFace: F, fontSize: 13.5, color: MUTED, margin: 0,
});
s.addText("Топ-10 уязвимостей считается за один проход по сетке — без пересчёта орбит; отказ применяется к сценарию прямо из таблицы", {
  x: M, y: 4.6, w: 3.7, h: 1.4, fontFace: F, fontSize: 13.5, color: TEXT_D, margin: 0,
});
s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 4.75, y: 1.8, w: 8.0, h: 4.8, fill: { color: "FFFFFF" }, line: { type: "none" }, rectRadius: 0.08, shadow: { type: "outer", color: "1B2A3A", blur: 8, offset: 2, angle: 90, opacity: 0.14 } });
s.addText("Что видит инженер при каждом отказе", { x: 5.1, y: 2.05, w: 7.3, h: 0.4, fontFace: F, fontSize: 16, bold: true, color: TEXT_D, margin: 0 });
const resRows = [
  ["Причина разрыва", "4 категории: нет видимого спутника / шлюз в отказе / нет контакта шлюза / разрыв ISL"],
  ["Перестроение маршрута", "новый путь или новый перерыв с точным интервалом [начало; конец)"],
  ["Δ по каждому пункту", "калькулятор «что если»: доступность и перерывы до/после отказа"],
  ["Резервные пути", "node-disjoint резерв и его доля по времени — оценка запаса прочности"],
];
resRows.forEach((r, i) => {
  const y = 2.6 + i * 0.98;
  s.addShape(pres.shapes.OVAL, { x: 5.1, y: y + 0.07, w: 0.13, h: 0.13, fill: { color: PRIMARY }, line: { type: "none" } });
  s.addText(r[0], { x: 5.42, y: y - 0.06, w: 7.0, h: 0.34, fontFace: F, fontSize: 14.5, bold: true, color: TEXT_D, margin: 0 });
  s.addText(r[1], { x: 5.42, y: y + 0.28, w: 7.05, h: 0.6, fontFace: F, fontSize: 12, color: MUTED, margin: 0 });
});

// --------------------------------- 7. Сравнение и рекомендация
s = pres.addSlide();
s.background = { color: BG_LIGHT };
orbit(s, false);
titleBar(s, "Рекомендация", "Критерий без «магических» весов");
const lex = [
  ["1", "максимум минимальной доступности по пунктам"],
  ["2", "затем максимум средней доступности"],
  ["3", "затем минимум худшего перерыва"],
  ["4", "затем минимум среднего числа переходов"],
];
lex.forEach((r, i) => {
  const x = M + i * 3.12;
  s.addShape(pres.shapes.OVAL, { x: x, y: 1.8, w: 0.46, h: 0.46, fill: { color: PRIMARY }, line: { type: "none" } });
  s.addText(r[0], { x: x, y: 1.8, w: 0.46, h: 0.46, fontFace: F, fontSize: 16, bold: true, color: "FFFFFF", align: "center", valign: "middle", margin: 0 });
  s.addText(r[1], { x: x + 0.6, y: 1.72, w: 2.4, h: 0.85, fontFace: F, fontSize: 12.5, color: TEXT_D, margin: 0 });
});
s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: M, y: 2.95, w: 12.13, h: 1.5, fill: { color: "FFF7E6" }, line: { type: "none" }, rectRadius: 0.08 });
s.addText([
  { text: "Вывод по проекту: ", options: { bold: true, color: TEXT_D } },
  { text: "цель ≥90% для всех северных пунктов достигается только полной группировкой (этап 3) при дальности МСC 3000 км — 96.7–98.9%. Ранняя очередь (этап 1) даёт лишь 12.6–27.2% с перерывами до 13 часов; ограничение МСC 2000 км снижает доступность до 62–78% — узкое место deliveries C70/C72.", options: { color: TEXT_D } },
], { x: M + 0.3, y: 3.18, w: 11.5, h: 1.1, fontFace: F, fontSize: 15, margin: 0 });
const cmp = [
  ["Полная группировка (этап 3)", "3 из 3 пунктов достигают цели", "2E7D32"],
  ["10 аппаратов в отказе", "0 из 3 · падение на ~17 п.п.", "C62828"],
  ["Ограничение МСC 2000 км", "0 из 3 · узкие места C70 и C72", "C62828"],
  ["Смещение RAAN/фазирования", "оценивается автоподбором за 20–60 прогонов", PRIMARY],
];
cmp.forEach((r, i) => {
  const y = 4.75 + i * 0.56;
  s.addShape(pres.shapes.OVAL, { x: M + 0.05, y: y + 0.09, w: 0.12, h: 0.12, fill: { color: r[2] }, line: { type: "none" } });
  s.addText(r[0], { x: M + 0.35, y: y, w: 5.6, h: 0.36, fontFace: F, fontSize: 14, bold: true, color: TEXT_D, margin: 0 });
  s.addText(r[1], { x: 7.0, y: y, w: 5.6, h: 0.36, fontFace: F, fontSize: 14, color: MUTED, margin: 0 });
});
srcLine(s, "Рекомендация строится по фактически рассчитанным метрикам; обоснование выводится в интерфейсе вместе с вариантом", false);

// ------------------------------------------- 8. Интерфейс (скриншот)
s = pres.addSlide();
s.background = { color: BG_DARK };
titleBar(s, "Интерфейс", "Всё на одном экране — без чтения документации", true);
s.addImage({ path: IMG("ui_overview.png"), x: M, y: 1.72, w: 9.1, h: 5.69 * 0.905, sizing: { type: "cover", w: 9.1, h: 5.15 } });
s.addText("Дашборд: карточки пунктов с целевым уровнем, шкала состояний, карта треков, таблица метрик", {
  x: 9.95, y: 2.1, w: 2.9, h: 2.6, fontFace: F, fontSize: 14, color: TEXT_L, margin: 0,
});
s.addText("Вкладки: Обзор · Сеть и время · Сравнение · Устойчивость · Экспорт · Методика", {
  x: 9.95, y: 4.9, w: 2.9, h: 1.6, fontFace: F, fontSize: 12, color: PRIMARY_SOFT, margin: 0,
});

// ------------------------------------------- 9. Качество и воспроизводимость
s = pres.addSlide();
s.background = { color: BG_LIGHT };
orbit(s, false);
titleBar(s, "Инженерное качество", "Проверяемо, воспроизводимо, готово к запуску");
const q = [
  { n: "86", t: "автотеста: валидация, границы отказов,\nмаршрутизация, метрики, экспорт, UI", c: PRIMARY },
  { n: "2×", t: "движка геометрии: официальный модуль\nи формулы документа — parity-тесты", c: PRIMARY },
  { n: "2160", t: "маршрутов в экспорте cosmo-A-result-1.0:\nкаждый путь валиден в свой момент", c: ACCENT },
  { n: "1", t: "команда на запуск: streamlit run app.py\nили docker run — без API-ключей", c: PRIMARY },
];
q.forEach((it, i) => {
  const x = M + i * 3.12;
  s.addText(it.n, { x: x, y: 1.9, w: 2.8, h: 1.05, fontFace: F, fontSize: 54, bold: true, color: it.c, margin: 0 });
  s.addText(it.t, { x: x, y: 3.0, w: 2.85, h: 1.0, fontFace: F, fontSize: 12.5, color: MUTED, margin: 0 });
});
s.addShape(pres.shapes.LINE, { x: M, y: 4.35, w: W - 2 * M, h: 0, line: { color: PRIMARY_SOFT, width: 1 } });
s.addText("Воспроизводимость", { x: M, y: 4.55, w: 6, h: 0.4, fontFace: F, fontSize: 16, bold: true, color: TEXT_D, margin: 0 });
const repro = [
  "регрессионные числа зафиксированы тестами по всем 4 сценариям",
  "экспортированный effective_scenario загружается обратно и проходит полную валидацию",
  "детерминизм: те же входные данные дают бит-в-бит тот же результат (проверено тестами)",
];
s.addText(repro.map((t, i) => ({ text: t, options: { bullet: { code: "25B8", indent: 12 }, breakLine: i < repro.length - 1 } })), {
  x: M, y: 5.0, w: 12.1, h: 1.7, fontFace: F, fontSize: 14.5, color: TEXT_D, paraSpaceAfter: 8, margin: 0,
});

// ------------------------------------------- 10. План демонстрации
s = pres.addSlide();
s.background = { color: BG_LIGHT };
orbit(s, false);
titleBar(s, "Демонстрация ~3 минуты", "Живой сценарий для жюри");
const demo = [
  ["Полная группировка", "доступность 96.7–98.9%, цель достигнута всеми пунктами"],
  ["Сеть и время", "маршрут в 3D, слайдер времени, прыжок к перерыву и его причина"],
  ["Этап 3 → 1", "пересчёт: доступность 12.6–27.2%, перерывы до 13 часов"],
  ["Отказ спутника", "добавляем отказ из маршрута — перестроение или перерыв"],
  ["Сравнение", "два варианта: различия конфигурации, Δ метрик, рекомендация"],
  ["Экспорт", "result JSON на 2160 маршрутов и повторная загрузка сценария"],
];
demo.forEach((r, i) => {
  const col = i % 2, row = Math.floor(i / 2);
  const x = M + col * 6.25, y = 1.95 + row * 1.55;
  s.addShape(pres.shapes.OVAL, { x: x, y: y + 0.05, w: 0.5, h: 0.5, fill: { color: row === 2 && col === 1 ? ACCENT : PRIMARY }, line: { type: "none" } });
  s.addText(String(i + 1), { x: x, y: y + 0.05, w: 0.5, h: 0.5, fontFace: F, fontSize: 17, bold: true, color: "FFFFFF", align: "center", valign: "middle", margin: 0 });
  s.addText(r[0], { x: x + 0.68, y: y - 0.02, w: 5.2, h: 0.38, fontFace: F, fontSize: 16, bold: true, color: TEXT_D, margin: 0 });
  s.addText(r[1], { x: x + 0.68, y: y + 0.36, w: 5.2, h: 0.65, fontFace: F, fontSize: 12.5, color: MUTED, margin: 0 });
});

// ------------------------------------------- 11. Финал
s = pres.addSlide();
s.background = { color: BG_DARK };
s.addShape(pres.shapes.OVAL, { x: -3.2, y: 2.4, w: 9.5, h: 9.5, fill: { type: "none" }, line: { color: PRIMARY_MID, width: 1.3, transparency: 40 } });
s.addShape(pres.shapes.OVAL, { x: 4.05, y: 6.05, w: 0.16, h: 0.16, fill: { color: ACCENT }, line: { type: "none" } });
s.addText("РЕКОМЕНДАЦИЯ КОМАНДЫ", { x: M, y: 1.35, w: 10, h: 0.35, fontFace: F, fontSize: 13, bold: true, color: PRIMARY_SOFT, charSpacing: 3, margin: 0 });
s.addText("Развёртывать все три очереди\nи держать МСC 3000 км", {
  x: M, y: 1.8, w: 12.1, h: 1.9, fontFace: F, fontSize: 40, bold: true, color: TEXT_L, margin: 0, lineSpacing: 48,
});
s.addText([
  { text: "только эта конфигурация закрывает цель ≥90% для всех северных пунктов (96.7–98.9%)", options: { breakLine: true } },
  { text: "узкие места известны и измерены: критичные аппараты, перерывы по причинам, резерв путей", options: {} },
], { x: M, y: 3.9, w: 10.6, h: 1.0, fontFace: F, fontSize: 16, color: MUTED_L, margin: 0, paraSpaceAfter: 6 });
s.addShape(pres.shapes.LINE, { x: M, y: 5.3, w: 3.2, h: 0, line: { color: ACCENT, width: 2.5 } });
s.addText([
  { text: "github.com/ivergit88/cosmohak — публичный репозиторий", options: { breakLine: true, bold: true, color: TEXT_L } },
  { text: "python -m venv .venv · pip install -r requirements.txt · streamlit run app.py   |   docker run -p 8501:8501", options: { color: PRIMARY_SOFT } },
], { x: M, y: 5.55, w: 11.5, h: 1.0, fontFace: F, fontSize: 15, margin: 0, paraSpaceAfter: 6 });

pres.writeFile({ fileName: path.join(__dirname, "КосмоХакатон_защита.pptx") }).then(() => console.log("OK: КосмоХакатон_защита.pptx"));
