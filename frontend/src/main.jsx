import React, { useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import * as d3 from "d3";
import {
  AlertTriangle,
  ArrowDownRight,
  ArrowLeft,
  ArrowUpRight,
  BarChart3,
  Check,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Clock3,
  Github,
  LineChart,
  MapPinned,
  Minus,
  Search,
  Trophy,
  X,
} from "lucide-react";
import "./styles.css";

const API = {
  catalog: "/api/catalog",
  indicator: (id) => `/api/indicator/${id}`,
  map: "/static/data/italian-regions.geo.json",
};

const tabs = [
  { id: "map", label: "Mappa", icon: MapPinned },
  { id: "ranking", label: "Classifica", icon: BarChart3 },
  { id: "trend", label: "Serie storica", icon: LineChart },
];

const SORTS = [
  { id: "complete", label: "Completezza" },
  { id: "recent", label: "Più recente" },
  { id: "az", label: "A–Z" },
  { id: "theme", label: "Tema" },
];

const MAP_RAMP = (t) => d3.interpolate("#E7ECF3", "#15233B")(t);
const MISSING_FILL = "#E2E0D8";

function App() {
  const [catalog, setCatalog] = useState(null);
  const [mapData, setMapData] = useState(null);
  const [indicator, setIndicator] = useState(null);
  const [error, setError] = useState(null);

  const [view, setView] = useUrlState("view");
  const [selectedId, setSelectedId] = useUrlState("indicator");
  const [selectedYear, setSelectedYear] = useUrlState("year");
  const [selectedRegion, setSelectedRegion] = useUrlState("region");
  const [themeParam, setThemeParam] = useUrlState("theme");
  const [queryParam, setQueryParam] = useUrlState("q");
  const [sortParam, setSortParam] = useUrlState("sort");
  const [partialParam, setPartialParam] = useUrlState("partial");
  const [areaParam, setAreaParam] = useUrlState("area");
  const [yearFromParam, setYearFromParam] = useUrlState("yfrom");
  const [yearToParam, setYearToParam] = useUrlState("yto");

  const theme = themeParam || "Tutti";
  const query = queryParam || "";
  const sort = sortParam || "complete";
  const showPartial = partialParam === "1";
  const macroArea = areaParam || "Tutte";
  // Default to atlas, but a shared ?indicator=… link (no explicit view) opens the detail.
  const activeView =
    view === "detail" ? "detail" : view === "atlas" ? "atlas" : selectedId ? "detail" : "atlas";

  const [activeTab, setActiveTab] = useState("map");
  const pageViewKey = activeView === "detail" ? `detail:${selectedId || ""}` : "atlas";
  const lastPageViewKey = useRef(null);

  useEffect(() => {
    Promise.all([fetchJson(API.catalog), fetchJson(API.map)])
      .then(([catalogData, geo]) => {
        setCatalog(catalogData);
        setMapData(geo);
      })
      .catch(() => setError("Non è stato possibile caricare l'archivio degli indicatori."));
  }, []);

  useEffect(() => {
    if (activeView === "detail" && !selectedId) return;
    if (lastPageViewKey.current === pageViewKey) return;
    lastPageViewKey.current = pageViewKey;
    trackPageView({
      view_type: activeView,
      indicator_id: activeView === "detail" ? selectedId : undefined,
    });
  }, [activeView, selectedId, pageViewKey]);

  useEffect(() => {
    if (activeView !== "detail") {
      setActiveTab("map");
      return;
    }
  }, [activeView, selectedId]);

  // Load the selected indicator only when the detail view is active.
  useEffect(() => {
    if (activeView !== "detail" || !catalog) return;
    const id = selectedId || catalog.featured_indicator_id;
    if (!id) return;
    if (id !== selectedId) {
      setSelectedId(id);
      return;
    }
    fetchJson(API.indicator(id))
      .then((payload) => {
        setIndicator(payload);
        const years = payload.metadata.years;
        const regions = payload.metadata.regions;
        if (!selectedYear || !years.includes(Number(selectedYear))) {
          setSelectedYear(String(payload.metadata.year_max));
        }
        if (!selectedRegion || !regions.includes(selectedRegion)) {
          setSelectedRegion(regions[0]);
        }
      })
      .catch(() => setError("Indicatore non disponibile. Prova a selezionarne un altro."));
  }, [activeView, selectedId, catalog]);

  const openIndicator = (item) => {
    setSelectedId(item.id);
    setThemeParam(item.theme);
    setQueryParam(null);
    setView("detail");
    trackEvent("select_indicator", {
      indicator_id: item.id,
      indicator_name: item.name,
      indicator_theme: item.theme,
    });
    window.scrollTo({ top: 0, behavior: "auto" });
  };

  const backToAtlas = () => {
    setView("atlas");
    trackEvent("back_to_atlas");
    window.scrollTo({ top: 0, behavior: "auto" });
  };

  if (error) {
    return (
      <main className="app-shell">
        <SiteHeader />
        <ErrorState message={error} />
        <SiteFooter />
      </main>
    );
  }

  if (!catalog || !mapData) {
    return (
      <main className="app-shell">
        <SiteHeader />
        <LoadingState />
        <SiteFooter />
      </main>
    );
  }

  if (activeView === "detail") {
    return (
      <DetailView
        catalog={catalog}
        mapData={mapData}
        indicator={indicator}
        theme={theme}
        selectedId={selectedId}
        selectedYear={selectedYear}
        setSelectedYear={(value) => {
          setSelectedYear(value);
          trackEvent("change_year", { indicator_id: selectedId, year: value });
        }}
        selectedRegion={selectedRegion}
        setSelectedRegion={(value) => {
          setSelectedRegion(value);
          trackEvent("change_region", { indicator_id: selectedId, region: value });
        }}
        onSelectIndicator={(id) => {
          setSelectedId(id);
          trackEvent("select_sibling_indicator", { indicator_id: id });
        }}
        onBack={backToAtlas}
        activeTab={activeTab}
        setActiveTab={(value) => {
          setActiveTab(value);
          trackEvent("change_visualization", { view_type: value, indicator_id: selectedId });
        }}
      />
    );
  }

  return (
    <AtlasView
      catalog={catalog}
      theme={theme}
      setTheme={(value) => {
        setThemeParam(value === "Tutti" ? null : value);
        trackEvent("filter_theme", { theme: value });
      }}
      query={query}
      setQuery={(value) => setQueryParam(value || null)}
      sort={sort}
      setSort={(value) => {
        setSortParam(value === "complete" ? null : value);
        trackEvent("sort_indicators", { sort: value });
      }}
      showPartial={showPartial}
      setShowPartial={(value) => {
        setPartialParam(value ? "1" : null);
        trackEvent("toggle_partial_data", { enabled: value });
      }}
      macroArea={macroArea}
      setMacroArea={(value) => {
        setAreaParam(value === "Tutte" ? null : value);
        setThemeParam(null);
        trackEvent("filter_macro_area", { macro_area: value });
      }}
      yearFrom={yearFromParam ? Number(yearFromParam) : null}
      yearTo={yearToParam ? Number(yearToParam) : null}
      setYearRange={(from, to) => {
        setYearFromParam(from === null ? null : String(from));
        setYearToParam(to === null ? null : String(to));
        trackEvent("filter_year_range", { year_from: from, year_to: to });
      }}
      onOpen={openIndicator}
    />
  );
}

/* ------------------------------------------------------------------ */
/* Shared chrome                                                       */
/* ------------------------------------------------------------------ */

function SiteHeader({ children }) {
  return (
    <header className="masthead">
      <a className="brand" href="/" aria-label="Divario Italia — home">
        <span className="brand-mark">DI</span>
        <span className="brand-text">
          <strong>Divario Italia</strong>
          <small>Atlante degli indicatori territoriali</small>
        </span>
      </a>
      {children}
      <nav className="masthead__links" aria-label="Collegamenti">
        <a href="/regioni">Regioni</a>
        <a href="/temi">Temi</a>
        <a href="/qualita-della-vita">Qualità della vita</a>
        <a href="/blog">Blog</a>
        <a
          href="https://www.istat.it/sistema-informativo-6/banca-dati-territoriale-per-le-politiche-di-sviluppo/"
          target="_blank"
          rel="noreferrer"
        >
          Fonte Istat <ArrowUpRight size={13} />
        </a>
        <a href="https://github.com/nmaiese/diset-viz" target="_blank" rel="noreferrer" aria-label="GitHub">
          <Github size={17} />
        </a>
      </nav>
    </header>
  );
}

function SiteFooter() {
  const hasConsentPreferences = typeof window !== "undefined" && typeof window.diOpenConsentPreferences === "function";

  return (
    <footer className="site-footer">
      <span>
        Divario Italia · dati{" "}
        <a
          href="https://www.istat.it/sistema-informativo-6/banca-dati-territoriale-per-le-politiche-di-sviluppo/"
          target="_blank"
          rel="noreferrer"
        >
          Istat
        </a>
        , indicatori territoriali per le politiche di sviluppo
      </span>
      <span>
        <a href="/">Atlante</a> · <a href="/regioni">Regioni</a> · <a href="/temi">Temi</a> · <a href="/qualita-della-vita">Qualità della vita</a> · <a href="/blog">Blog</a> · <a href="/privacy">Privacy e cookie</a>
      </span>
      {hasConsentPreferences && (
        <button className="privacy-settings-link" type="button" onClick={() => window.diOpenConsentPreferences()}>
          Gestisci preferenze cookie
        </button>
      )}
    </footer>
  );
}

/* ------------------------------------------------------------------ */
/* Atlas (browse) view                                                */
/* ------------------------------------------------------------------ */

function AtlasView({
  catalog, theme, setTheme, query, setQuery, sort, setSort, showPartial, setShowPartial,
  macroArea, setMacroArea, yearFrom, yearTo, setYearRange, onOpen,
}) {
  const [fullMin, fullMax] = useMemo(() => {
    const mins = catalog.indicators.map((i) => i.year_min);
    const maxs = catalog.indicators.map((i) => i.year_max);
    return [Math.min(...mins), Math.max(...maxs)];
  }, [catalog]);

  // Themes belonging to the selected macro-area (the spine narrows with the area).
  const areaThemes = useMemo(() => {
    if (macroArea === "Tutte") return catalog.themes;
    const inArea = new Set((catalog.macro_areas || []).find((a) => a.name === macroArea)?.themes || []);
    return catalog.themes.filter((t) => inArea.has(t.name));
  }, [catalog, macroArea]);

  const pool = useMemo(() => {
    let list = showPartial ? catalog.indicators : catalog.indicators.filter((i) => i.complete);
    if (macroArea !== "Tutte") list = list.filter((i) => i.macro_area === macroArea);
    // Year coverage: only the bounds the user actually set constrain the list.
    // "Dal X" keeps series that reach back to X; "Al Y" keeps series that run up to Y.
    if (yearFrom != null) list = list.filter((i) => i.year_min <= yearFrom);
    if (yearTo != null) list = list.filter((i) => i.year_max >= yearTo);
    return list;
  }, [catalog, showPartial, macroArea, yearFrom, yearTo]);

  const themeCounts = useMemo(() => {
    const counts = new Map();
    for (const item of pool) counts.set(item.theme, (counts.get(item.theme) || 0) + 1);
    return counts;
  }, [pool]);

  const filtered = useMemo(() => {
    let list = pool;
    if (theme !== "Tutti") list = list.filter((i) => i.theme === theme);
    const nq = normalizeText(query);
    if (nq) {
      list = list.filter((i) => normalizeText(`${i.name} ${i.theme} ${i.archive}`).includes(nq));
    }
    return [...list].sort(SORTERS[sort] || SORTERS.complete);
  }, [pool, theme, query, sort]);

  const completeTotal = useMemo(() => catalog.indicators.filter((i) => i.complete).length, [catalog]);

  return (
    <main className="app-shell">
      <SiteHeader />

      <section className="atlas-hero">
        <p className="eyebrow">Istat · {catalog.indicators.length} indicatori · 20 regioni · {coverageSpan(catalog)}</p>
        <h1>
          Un atlante per leggere l'Italia,<br />
          regione per regione.
        </h1>
        <p className="atlas-hero__lead">
          Centinaia di indicatori Istat per capire dove l'Italia corre e dove resta indietro.
          Filtra per area, tema o anni, poi apri la scheda di ogni indicatore con mappa,
          classifica e andamento nel tempo.
        </p>
      </section>

      <MacroSpine
        areas={catalog.macro_areas || []}
        selected={macroArea}
        onSelect={setMacroArea}
      />

      <section className="atlas">
        <ThemeSpine
          themes={areaThemes}
          counts={themeCounts}
          total={pool.length}
          selected={theme}
          onSelect={setTheme}
        />

        <div className="index-panel">
          <CommandBar
            query={query}
            setQuery={setQuery}
            sort={sort}
            setSort={setSort}
            showPartial={showPartial}
            setShowPartial={setShowPartial}
            count={filtered.length}
            completeTotal={completeTotal}
            fullMin={fullMin}
            fullMax={fullMax}
            yearFrom={yearFrom}
            yearTo={yearTo}
            setYearRange={setYearRange}
          />
          <IndicatorIndex items={filtered} onOpen={onOpen} />
        </div>
      </section>
      <SiteFooter />
    </main>
  );
}

function MacroSpine({ areas, selected, onSelect }) {
  if (!areas.length) return null;
  return (
    <nav className="macro-spine wrap" aria-label="Filtra per area">
      <button
        type="button"
        className={selected === "Tutte" ? "macro-tab is-active" : "macro-tab"}
        onClick={() => onSelect("Tutte")}
      >
        Tutte le aree
      </button>
      {areas.map((area) => (
        <button
          key={area.name}
          type="button"
          className={selected === area.name ? "macro-tab is-active" : "macro-tab"}
          onClick={() => onSelect(area.name)}
        >
          {area.name} <em>{area.indicator_count}</em>
        </button>
      ))}
    </nav>
  );
}

function ThemeSpine({ themes, counts, total, selected, onSelect }) {
  const ordered = [...themes].sort((a, b) => (counts.get(b.name) || 0) - (counts.get(a.name) || 0));
  return (
    <aside className="theme-spine" aria-label="Filtra per tema">
      <h2>Temi</h2>
      <ul>
        <li>
          <button className={selected === "Tutti" ? "is-active" : ""} onClick={() => onSelect("Tutti")} type="button">
            <span>Tutti</span>
            <em>{total}</em>
          </button>
        </li>
        {ordered.map((item) => {
          const count = counts.get(item.name) || 0;
          return (
            <li key={item.name}>
              <button
                className={selected === item.name ? "is-active" : ""}
                onClick={() => onSelect(item.name)}
                disabled={count === 0}
                type="button"
              >
                <span>{item.name}</span>
                <em>{count}</em>
              </button>
            </li>
          );
        })}
      </ul>
    </aside>
  );
}

function CommandBar({
  query, setQuery, sort, setSort, showPartial, setShowPartial, count, completeTotal,
  fullMin, fullMax, yearFrom, yearTo, setYearRange,
}) {
  const years = useMemo(() => {
    const list = [];
    for (let y = fullMin; y <= fullMax; y += 1) list.push(y);
    return list;
  }, [fullMin, fullMax]);

  const yearActive = yearFrom != null || yearTo != null;
  // Sentinel "" means no bound on that side. Keep the window coherent: if the two
  // bounds cross, pull the other one along so you never ask for an empty interval.
  const onFrom = (raw) => {
    const value = raw === "" ? null : Number(raw);
    setYearRange(value, value != null && yearTo != null && yearTo < value ? value : yearTo);
  };
  const onTo = (raw) => {
    const value = raw === "" ? null : Number(raw);
    setYearRange(value != null && yearFrom != null && yearFrom > value ? value : yearFrom, value);
  };

  let yearLabel = "";
  if (yearFrom != null && yearTo != null) yearLabel = `con dati dal ${yearFrom} al ${yearTo}`;
  else if (yearFrom != null) yearLabel = `con storico dal ${yearFrom}`;
  else if (yearTo != null) yearLabel = `aggiornati al ${yearTo}`;

  return (
    <div className="command-bar">
      <label className="search-box">
        <Search size={18} />
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Cerca: turismo, occupazione, rifiuti, banda larga…"
          aria-label="Cerca un indicatore"
        />
      </label>
      <div className="command-bar__controls">
        <div className={yearActive ? "year-range is-active" : "year-range"}>
          <span className="year-range__label">Anni</span>
          <label className="select-field select-field--year">
            <span>Dal</span>
            <select value={yearFrom ?? ""} onChange={(event) => onFrom(event.target.value)}>
              <option value="">Da sempre</option>
              {years.map((y) => <option key={y} value={y}>{y}</option>)}
            </select>
            <ChevronDown className="select-icon" size={15} />
          </label>
          <label className="select-field select-field--year">
            <span>Al</span>
            <select value={yearTo ?? ""} onChange={(event) => onTo(event.target.value)}>
              <option value="">A oggi</option>
              {years.map((y) => <option key={y} value={y}>{y}</option>)}
            </select>
            <ChevronDown className="select-icon" size={15} />
          </label>
          {yearActive && (
            <button
              type="button"
              className="year-range__reset"
              onClick={() => setYearRange(null, null)}
              aria-label="Azzera il filtro anni"
            >
              <X size={14} />
            </button>
          )}
        </div>
        <label className="select-field">
          <span>Ordina</span>
          <select value={sort} onChange={(event) => setSort(event.target.value)}>
            {SORTS.map((option) => (
              <option key={option.id} value={option.id}>{option.label}</option>
            ))}
          </select>
          <ChevronDown className="select-icon" size={15} />
        </label>
        <button
          type="button"
          className={showPartial ? "toggle is-on" : "toggle"}
          aria-pressed={showPartial}
          onClick={() => setShowPartial(!showPartial)}
        >
          <span className="toggle__dot" /> Mostra anche parziali
        </button>
      </div>
      <p className="command-bar__count">
        <strong>{count}</strong> {count === 1 ? "indicatore" : "indicatori"}
        {yearActive && <span> · {yearLabel}</span>}
        {!showPartial && <span> · solo dati completi ({completeTotal})</span>}
      </p>
    </div>
  );
}

function IndicatorIndex({ items, onOpen }) {
  if (!items.length) {
    return (
      <p className="card-empty">
        Nessun indicatore corrisponde ai filtri. Prova a cambiare tema o ad attivare i dati parziali.
      </p>
    );
  }
  return (
    <ol className="indicator-index">
      {items.map((item) => (
        <IndexRow key={item.id} item={item} onOpen={onOpen} />
      ))}
    </ol>
  );
}

function IndexRow({ item, onOpen }) {
  const delta = sparkDelta(item.spark);
  return (
    <li>
      <button className="index-row" onClick={() => onOpen(item)} type="button">
        <span className="index-row__main">
          <small className="index-row__theme">{item.theme}</small>
          <strong className="index-row__name">{item.name}</strong>
          <CoverageBadge item={item} />
        </span>
        <span className="index-row__spark">
          <Sparkline data={item.spark} width={150} height={40} />
        </span>
        <span className="index-row__meta">
          {delta !== null && (
            <span className={`index-row__delta ${delta >= 0 ? "is-up" : "is-down"}`}>
              {delta >= 0 ? <ArrowUpRight size={14} /> : <ArrowDownRight size={14} />}
              {formatDelta(delta)}
            </span>
          )}
          <small>{item.unit}</small>
        </span>
        <ChevronRight className="index-row__chevron" size={18} />
      </button>
    </li>
  );
}

function CoverageBadge({ item }) {
  return (
    <span className="coverage">
      <span className="coverage__pill">{item.region_count} reg.</span>
      <span className="coverage__pill">{item.year_min}–{item.year_max}</span>
      {item.complete ? (
        <span className="coverage__pill is-complete"><Check size={12} /> completo</span>
      ) : (
        <span className="coverage__pill is-partial">{Math.round(item.completeness * 100)}% dati</span>
      )}
    </span>
  );
}

/* ------------------------------------------------------------------ */
/* Detail (dashboard) view                                            */
/* ------------------------------------------------------------------ */

function DetailView({
  catalog,
  mapData,
  indicator,
  theme,
  selectedId,
  selectedYear,
  setSelectedYear,
  selectedRegion,
  setSelectedRegion,
  onSelectIndicator,
  onBack,
  activeTab,
  setActiveTab,
}) {
  // Only treat the indicator as ready when its payload matches the selected id,
  // so switching indicators never flashes the previous chart.
  const ready = indicator && String(indicator.metadata.id) === String(selectedId);
  const indicatorMeta = ready ? indicator.metadata : null;
  const year = Number(selectedYear);

  const yearValues = useMemo(() => valuesForYear(indicator?.series || [], year), [indicator, year]);
  const regionSeries = useMemo(
    () => valuesForRegion(indicator?.series || [], selectedRegion),
    [indicator, selectedRegion],
  );
  const insights = useMemo(
    () => buildInsights(indicatorMeta, indicator?.series || [], yearValues, selectedRegion),
    [indicatorMeta, indicator, yearValues, selectedRegion],
  );

  const siblings = useMemo(() => {
    const themeName = indicatorMeta?.theme || theme;
    return catalog.indicators
      .filter((item) => item.theme === themeName)
      .sort((a, b) => a.name.localeCompare(b.name, "it"));
  }, [catalog, indicatorMeta, theme]);

  const siblingIndex = siblings.findIndex((item) => item.id === selectedId);
  const prev = siblingIndex > 0 ? siblings[siblingIndex - 1] : null;
  const next = siblingIndex >= 0 && siblingIndex < siblings.length - 1 ? siblings[siblingIndex + 1] : null;

  return (
    <main className="app-shell">
      <SiteHeader>
        <button className="back-link" type="button" onClick={onBack}>
          <ArrowLeft size={16} /> Atlante
        </button>
      </SiteHeader>

      {!indicatorMeta ? (
        <LoadingState />
      ) : (
        <>
          <nav className="breadcrumb" aria-label="Percorso">
            <button type="button" onClick={onBack}>Atlante</button>
            <span>/</span>
            <span>{indicatorMeta.theme}</span>
          </nav>

          <section className="workspace" id="dashboard">
            <aside className="indicator-panel">
              <IndicatorHeader metadata={indicatorMeta} regionCount={yearValues.length} />
              <Controls
                metadata={indicatorMeta}
                selectedYear={year}
                setSelectedYear={(value) => setSelectedYear(String(value))}
                selectedRegion={selectedRegion}
                setSelectedRegion={setSelectedRegion}
              />
              <InsightPanel insights={insights} unit={indicatorMeta.unit} year={year} region={selectedRegion} />
              {siblings.length > 1 && (
                <div className="sibling-nav">
                  <button type="button" disabled={!prev} onClick={() => prev && onSelectIndicator(prev.id)}>
                    <ChevronLeft size={16} /> Precedente
                  </button>
                  <button type="button" disabled={!next} onClick={() => next && onSelectIndicator(next.id)}>
                    Successivo <ChevronRight size={16} />
                  </button>
                </div>
              )}
            </aside>

            <section className="viz-stage">
              <div className="mobile-tabs" role="tablist" aria-label="Viste">
                {tabs.map((tab) => {
                  const Icon = tab.icon;
                  return (
                    <button
                      key={tab.id}
                      className={activeTab === tab.id ? "is-active" : ""}
                      onClick={() => setActiveTab(tab.id)}
                      type="button"
                    >
                      <Icon size={16} /> {tab.label}
                    </button>
                  );
                })}
              </div>

              <div className={`viz-grid active-${activeTab}`}>
                <DataCard className="map-card" title="Mappa regionale" kicker={String(year)}>
                  <ItalyMap
                    geo={mapData}
                    values={yearValues}
                    selectedRegion={selectedRegion}
                    onSelect={setSelectedRegion}
                    unit={indicatorMeta.unit}
                  />
                </DataCard>
                <DataCard className="ranking-card" title="Classifica" kicker={`${year} · ${indicatorMeta.unit}`}>
                  <Ranking
                    values={yearValues}
                    selectedRegion={selectedRegion}
                    onSelect={setSelectedRegion}
                    unit={indicatorMeta.unit}
                  />
                </DataCard>
                <DataCard className="timeline-card" title="Serie storica" kicker={selectedRegion}>
                  <Timeline
                    series={indicator.series}
                    regionSeries={regionSeries}
                    selectedRegion={selectedRegion}
                    selectedYear={year}
                    setSelectedYear={(value) => setSelectedYear(String(value))}
                    unit={indicatorMeta.unit}
                  />
                </DataCard>
              </div>
            </section>
          </section>
        </>
      )}
      <SiteFooter />
    </main>
  );
}

function stripAccents(value) {
  return (value || "").normalize("NFKD").replace(/[̀-ͯ]/g, "");
}

// Mirrors app/profiles.py indicator_slug. The server 301s to the canonical slug,
// so minor differences still resolve.
function indicatorSlug(name) {
  return stripAccents(name)
    .toLowerCase()
    .replace(/'/g, " ")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 80)
    .replace(/-+$/, "");
}

function indicatorPath(id, name) {
  const slug = indicatorSlug(name);
  return slug ? `/indicatore/${id}-${slug}` : `/indicatore/${id}`;
}

// Mirrors app/profiles.py region_key_for / data.py _slugify.
function regionKey(region) {
  return stripAccents(region).toLowerCase().replace(/'/g, " ").replace(/ /g, "-");
}

function IndicatorHeader({ metadata, regionCount }) {
  return (
    <div className="indicator-header">
      <span className="tag">{metadata.theme}</span>
      <h2>{metadata.name}</h2>
      <p className="indicator-header__seo">
        <a href={indicatorPath(metadata.id, metadata.name)}>Scheda completa e classifica regioni →</a>
      </p>
      {metadata.explain && <IndicatorExplain explain={metadata.explain} />}
      {metadata.archive && (
        <p className="indicator-header__def">
          <small>Definizione</small>
          {metadata.archive}
        </p>
      )}
      <dl>
        <div><dt>Unità di misura</dt><dd>{metadata.unit || "—"}</dd></div>
        <div><dt>Copertura</dt><dd>{metadata.year_min}–{metadata.year_max}</dd></div>
        <div><dt>Regioni</dt><dd>{regionCount || metadata.regions.length}/20</dd></div>
        <div><dt>Fonte</dt><dd>{metadata.source_url ? (<a href={metadata.source_url} target="_blank" rel="noreferrer">{metadata.source_label || metadata.source}</a>) : (metadata.source_label || metadata.source)}</dd></div>
      </dl>
    </div>
  );
}

function IndicatorExplain({ explain }) {
  const detailRows = [
    ["Esempio", explain.example?.replace(/^Esempio:\s*/, "")],
    ["Come leggerlo", explain.reading],
    ["Attenzione", explain.caveat],
  ].filter(([, value]) => value);

  if (!explain.plain && !detailRows.length) return null;

  return (
    <section className="indicator-explain" aria-label="Spiegazione dell'indicatore">
      {explain.plain && (
        <p className="indicator-explain__lead">
          <small>In breve</small>
          {explain.plain}
        </p>
      )}
      {!!detailRows.length && (
        <details className="indicator-explain__details">
          <summary>Leggi esempio e avvertenze</summary>
          <div>
            {detailRows.map(([label, value]) => (
              <p key={label}>
                <small>{label}</small>
                {value}
              </p>
            ))}
          </div>
        </details>
      )}
    </section>
  );
}

function InsightPanel({ insights, unit, year, region }) {
  const TrendIcon = insights.delta > 0 ? ArrowUpRight : insights.delta < 0 ? ArrowDownRight : Minus;
  const trendClass = insights.delta > 0 ? "is-up" : insights.delta < 0 ? "is-down" : "is-flat";
  return (
    <div className="insights">
      <div className="insight insight--region">
        <small>{region || "Regione"} · {year}</small>
        <strong>{formatValue(insights.regionEntry?.value, unit)}</strong>
        <span>
          {insights.regionRank
            ? `${insights.regionRank}ª su ${insights.total} regioni`
            : "Dato non disponibile per quest'anno"}
        </span>
        {region && <a className="insight__link" href={`/regione/${regionKey(region)}`}>Profilo di {region} →</a>}
      </div>
      <div className="insight">
        <small><Trophy size={13} /> Valore più alto · {year}</small>
        <strong>{insights.top?.region || "—"}</strong>
        <span>{formatValue(insights.top?.value, unit)}</span>
      </div>
      <div className="insight">
        <small>Valore più basso · {year}</small>
        <strong>{insights.bottom?.region || "—"}</strong>
        <span>{formatValue(insights.bottom?.value, unit)}</span>
      </div>
      <div className={`insight insight--trend ${trendClass}`}>
        <small><TrendIcon size={13} /> {region} · trend storico</small>
        <strong>{insights.trendLabel}</strong>
        <span>{insights.trendText}</span>
      </div>
    </div>
  );
}

function Controls({ metadata, selectedYear, setSelectedYear, selectedRegion, setSelectedRegion }) {
  return (
    <div className="controls">
      <label className="select-field">
        <span><Clock3 size={15} /> Anno</span>
        <select value={selectedYear} onChange={(event) => setSelectedYear(Number(event.target.value))}>
          {metadata.years.map((year) => <option key={year} value={year}>{year}</option>)}
        </select>
        <ChevronDown className="select-icon" size={16} />
      </label>
      <label className="select-field">
        <span><MapPinned size={15} /> Regione</span>
        <select value={selectedRegion} onChange={(event) => setSelectedRegion(event.target.value)}>
          {metadata.regions.map((region) => <option key={region} value={region}>{region}</option>)}
        </select>
        <ChevronDown className="select-icon" size={16} />
      </label>
    </div>
  );
}

function DataCard({ title, kicker, className, children }) {
  return (
    <article className={`data-card ${className || ""}`}>
      <header>
        <div>
          <small>{kicker}</small>
          <h3>{title}</h3>
        </div>
      </header>
      {children}
    </article>
  );
}

function ItalyMap({ geo, values, selectedRegion, onSelect, unit }) {
  const width = 560;
  const height = 660;
  const valueByKey = useMemo(() => new Map(values.map((row) => [row.region_key, row])), [values]);
  const numericValues = values.map((row) => row.value).filter((value) => value !== null && Number.isFinite(value));
  const hasData = numericValues.length > 0;
  const min = hasData ? Math.min(...numericValues) : 0;
  const max = hasData ? Math.max(...numericValues) : 1;
  const color = d3.scaleSequential(MAP_RAMP).domain(min === max ? [min, min + 1] : [min, max]);
  // Fit the whole country to the viewBox so it is always centred and never clipped.
  const path = useMemo(() => {
    const projection = d3.geoMercator().fitExtent([[14, 14], [width - 14, height - 14]], geo);
    return d3.geoPath(projection);
  }, [geo]);

  return (
    <div className="map-wrap">
      <svg className="italy-map" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Mappa delle regioni italiane">
        {geo.features.map((feature) => {
          const key = normalizeRegionKey(feature.properties.name);
          const row = valueByKey.get(key);
          const hasValue = row && row.value !== null && row.value !== undefined && Number.isFinite(row.value);
          const isSelected = row?.region === selectedRegion;
          return (
            <path
              key={key}
              d={path(feature)}
              className={isSelected ? "is-selected" : ""}
              fill={hasValue ? color(row.value) : MISSING_FILL}
              onClick={() => row && onSelect(row.region)}
              tabIndex={0}
              role="button"
              aria-label={row ? `${row.region}: ${formatValue(row.value, unit)}` : feature.properties.name}
              onKeyDown={(event) => {
                if ((event.key === "Enter" || event.key === " ") && row) {
                  event.preventDefault();
                  onSelect(row.region);
                }
              }}
            >
              <title>{row ? `${row.region}: ${formatValue(row.value, unit)}` : feature.properties.name}</title>
            </path>
          );
        })}
      </svg>
      {hasData ? (
        <MapLegend min={min} max={max} unit={unit} />
      ) : (
        <p className="map-empty">Nessun dato disponibile per l'anno selezionato.</p>
      )}
    </div>
  );
}

function MapLegend({ min, max, unit }) {
  const stops = d3.range(0, 1.0001, 0.1);
  const gradient = `linear-gradient(90deg, ${stops.map((s) => MAP_RAMP(s)).join(", ")})`;
  const mid = min + (max - min) / 2;
  return (
    <div className="map-legend" aria-hidden="true">
      <div className="map-legend__bar" style={{ background: gradient }} />
      <div className="map-legend__scale">
        <span>{formatCompact(min, unit)}</span>
        <span>{formatCompact(mid, unit)}</span>
        <span>{formatCompact(max, unit)}</span>
      </div>
      <div className="map-legend__note">
        <span className="map-legend__swatch" style={{ background: MISSING_FILL }} /> dato non disponibile
      </div>
    </div>
  );
}

function Ranking({ values, selectedRegion, onSelect, unit }) {
  if (!values.length) {
    return <p className="card-empty">Nessuna regione con dati per l'anno selezionato.</p>;
  }
  const max = Math.max(...values.map((row) => row.value || 0), 1);
  return (
    <div className="ranking">
      {values.map((row, index) => (
        <button
          key={row.region}
          className={row.region === selectedRegion ? "ranking-row is-active" : "ranking-row"}
          onClick={() => onSelect(row.region)}
          type="button"
        >
          <span className="rank">{index + 1}</span>
          <span className="region">{row.region}</span>
          <span className="bar"><i style={{ width: `${Math.max((row.value / max) * 100, 2)}%` }} /></span>
          <strong>{formatValue(row.value, unit)}</strong>
        </button>
      ))}
    </div>
  );
}

function Timeline({ series, regionSeries, selectedRegion, selectedYear, setSelectedYear, unit }) {
  const width = 760;
  const height = 300;
  const margin = { top: 20, right: 28, bottom: 36, left: 60 };
  const averageSeries = useMemo(() => buildAverageSeries(series), [series]);
  const regionPoints = regionSeries.filter((row) => Number.isFinite(row.value));
  const allValues = [...regionPoints, ...averageSeries].map((row) => row.value).filter(Number.isFinite);
  const allYears = [...regionPoints, ...averageSeries].map((row) => row.year);

  if (allValues.length < 1 || allYears.length < 1) {
    return <p className="card-empty">Serie storica non disponibile per questa regione.</p>;
  }

  const x = d3.scaleLinear().domain(d3.extent(allYears)).range([margin.left, width - margin.right]);
  const y = d3.scaleLinear().domain(d3.extent(allValues)).nice().range([height - margin.bottom, margin.top]);
  const line = d3.line().defined((row) => Number.isFinite(row.value)).x((row) => x(row.year)).y((row) => y(row.value));

  return (
    <div className="timeline-wrap">
      <div className="timeline-legend">
        <span className="legend-item legend-region"><i /> {selectedRegion}</span>
        <span className="legend-item legend-average"><i /> Media nazionale</span>
      </div>
      <svg className="timeline" viewBox={`0 0 ${width} ${height}`} role="img" aria-label={`Serie storica di ${selectedRegion}`}>
        <text className="axis-title" x={16} y={margin.top + 4}>{unit}</text>
        <g className="grid">
          {y.ticks(4).map((tick) => (
            <g key={tick}>
              <line x1={margin.left} x2={width - margin.right} y1={y(tick)} y2={y(tick)} />
              <text x={margin.left - 10} y={y(tick)}>{formatCompact(tick, unit)}</text>
            </g>
          ))}
        </g>
        <path className="average-line" d={line(averageSeries)} />
        <path className="region-line" d={line(regionPoints)} />
        {regionPoints.map((row) => (
          <circle
            key={row.year}
            className={row.year === selectedYear ? "is-active" : ""}
            cx={x(row.year)}
            cy={y(row.value)}
            r={row.year === selectedYear ? 7 : 4}
            tabIndex={0}
            role="button"
            aria-label={`${row.year}: ${formatValue(row.value, unit)}`}
            onClick={() => setSelectedYear(row.year)}
            onKeyDown={(event) => {
              if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                setSelectedYear(row.year);
              }
            }}
          >
            <title>{row.year}: {formatValue(row.value, unit)}</title>
          </circle>
        ))}
        <g className="x-axis">
          {x.ticks(6).map((tick) => <text key={tick} x={x(tick)} y={height - 10}>{Math.round(tick)}</text>)}
        </g>
      </svg>
    </div>
  );
}

function Sparkline({ data, width = 150, height = 40 }) {
  const points = (data || []).filter((row) => Number.isFinite(row.value));
  if (points.length < 2) {
    return <svg className="spark spark--empty" viewBox={`0 0 ${width} ${height}`} aria-hidden="true" />;
  }
  const pad = 3;
  const x = d3.scaleLinear().domain(d3.extent(points, (row) => row.year)).range([pad, width - pad]);
  const y = d3.scaleLinear().domain(d3.extent(points, (row) => row.value)).range([height - pad, pad]);
  const line = d3.line().x((row) => x(row.year)).y((row) => y(row.value)).curve(d3.curveMonotoneX);
  const last = points[points.length - 1];
  return (
    <svg className="spark" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Andamento medio nazionale" preserveAspectRatio="none">
      <path className="spark__line" d={line(points)} />
      <circle className="spark__dot" cx={x(last.year)} cy={y(last.value)} r={2.6} />
    </svg>
  );
}

function LoadingState() {
  return (
    <section className="loading-state">
      <span />
      <p>Preparazione degli indicatori territoriali…</p>
    </section>
  );
}

function ErrorState({ message }) {
  return (
    <section className="error-state" role="alert">
      <AlertTriangle size={32} />
      <p>{message}</p>
      <button type="button" onClick={() => window.location.reload()}>Riprova</button>
    </section>
  );
}

/* ------------------------------------------------------------------ */
/* Helpers                                                            */
/* ------------------------------------------------------------------ */

const SORTERS = {
  complete: (a, b) =>
    b.completeness - a.completeness || b.year_max - a.year_max || a.name.localeCompare(b.name, "it"),
  recent: (a, b) => b.year_max - a.year_max || b.completeness - a.completeness || a.name.localeCompare(b.name, "it"),
  az: (a, b) => a.name.localeCompare(b.name, "it"),
  theme: (a, b) => a.theme.localeCompare(b.theme, "it") || a.name.localeCompare(b.name, "it"),
};

function useUrlState(key) {
  const [value, setValue] = useState(() => new URLSearchParams(window.location.search).get(key));
  const update = (nextValue) => {
    setValue(nextValue);
    const url = new URL(window.location.href);
    if (nextValue) url.searchParams.set(key, nextValue);
    else url.searchParams.delete(key);
    window.history.replaceState({}, "", url);
  };
  return [value, update];
}

async function fetchJson(url) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`Request failed: ${url}`);
  return response.json();
}

function coverageSpan(catalog) {
  const mins = catalog.indicators.map((i) => i.year_min);
  const maxs = catalog.indicators.map((i) => i.year_max);
  return `${Math.min(...mins)}–${Math.max(...maxs)}`;
}

function sparkDelta(spark) {
  const points = (spark || []).filter((row) => Number.isFinite(row.value));
  if (points.length < 2) return null;
  const first = points[0].value;
  const last = points[points.length - 1].value;
  if (!Number.isFinite(first) || first === 0) return null;
  return (last - first) / Math.abs(first);
}

function valuesForYear(series, year) {
  return series
    .filter((row) => row.year === year && row.value !== null)
    .sort((a, b) => b.value - a.value);
}

function valuesForRegion(series, region) {
  return series
    .filter((row) => row.region === region && row.value !== null)
    .sort((a, b) => a.year - b.year);
}

function buildAverageSeries(series) {
  const byYear = d3.group(series.filter((row) => row.value !== null), (row) => row.year);
  return Array.from(byYear, ([year, rows]) => ({
    year,
    value: d3.mean(rows, (row) => row.value),
  })).sort((a, b) => a.year - b.year);
}

function buildInsights(metadata, series, yearValues, selectedRegion) {
  const top = yearValues[0];
  const bottom = yearValues[yearValues.length - 1];
  const total = yearValues.length;
  const regionIndex = yearValues.findIndex((row) => row.region === selectedRegion);
  const regionEntry = regionIndex >= 0 ? yearValues[regionIndex] : null;
  const regionRank = regionIndex >= 0 ? regionIndex + 1 : null;

  const regionRows = valuesForRegion(series, selectedRegion);
  const first = regionRows[0];
  const last = regionRows[regionRows.length - 1];
  const delta = first && last ? last.value - first.value : null;
  const trendLabel = delta === null ? "—" : delta > 0 ? "In crescita" : delta < 0 ? "In calo" : "Stabile";
  const trendText = first && last
    ? `${formatValue(first.value, metadata?.unit)} → ${formatValue(last.value, metadata?.unit)} (${first.year}–${last.year})`
    : "Serie non disponibile";

  return { top, bottom, total, regionEntry, regionRank, delta, trendLabel, trendText };
}

function normalizeText(value) {
  return (value || "").normalize("NFKD").replace(/[̀-ͯ]/g, "").toLowerCase();
}

function normalizeRegionKey(value) {
  return value.toLowerCase().replace(/'/g, " ").replace(/\s+/g, "-");
}

function formatValue(value, unit = "") {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  const digits = Math.abs(value) >= 100 ? 0 : 2;
  const formatted = new Intl.NumberFormat("it-IT", { maximumFractionDigits: digits }).format(value);
  return unit ? `${formatted} ${unit}` : formatted;
}

function formatPercent(ratio) {
  if (!Number.isFinite(ratio)) return "";
  const pct = ratio * 100;
  const digits = Math.abs(pct) >= 10 ? 0 : 1;
  const formatted = new Intl.NumberFormat("it-IT", {
    maximumFractionDigits: digits,
    signDisplay: "always",
  }).format(pct);
  return `${formatted}%`;
}

function formatDelta(ratio) {
  if (!Number.isFinite(ratio)) return "";
  // Growth from a near-zero base produces huge percentages; show a multiplier instead.
  if (ratio >= 5) {
    return `×${new Intl.NumberFormat("it-IT", { maximumFractionDigits: 0 }).format(1 + ratio)}`;
  }
  return formatPercent(ratio);
}

function isPercentUnit(unit = "") {
  const u = unit.toLowerCase();
  return u.includes("percentuale") || u.includes("per 100") || u === "%";
}

function formatCompact(value, unit = "") {
  if (!Number.isFinite(value)) return "";
  const formatted = new Intl.NumberFormat("it-IT", {
    notation: Math.abs(value) > 9999 ? "compact" : "standard",
    maximumFractionDigits: 1,
  }).format(value);
  return isPercentUnit(unit) ? `${formatted}%` : formatted;
}

function trackEvent(name, params = {}) {
  if (typeof window === "undefined") return;
  const eventParams = buildAnalyticsParams(params);
  pushDataLayerEvent(name, eventParams);
  trackInternalEvent(name, eventParams);
}

function trackPageView() {
  if (typeof window === "undefined") return;
  trackEvent("page_view", {
    page_location: window.location.href,
    page_path: `${window.location.pathname}${window.location.search}`,
    page_title: document.title,
  });
}

function trackInternalEvent(name, params = {}) {
  const body = JSON.stringify({
    name,
    params,
    path: `${window.location.pathname}${window.location.search}`,
    title: document.title,
  });

  try {
    fetch("/api/events", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body,
      keepalive: true,
      credentials: "omit",
    }).catch(() => {});
  } catch (_) {}
}

function pushDataLayerEvent(name, params = {}) {
  window.dataLayer = window.dataLayer || [];
  window.dataLayer.push({
    event: name,
    ...params,
  });
}

function buildAnalyticsParams(params = {}) {
  return {
    page_type: currentPageType(),
    page_path: `${window.location.pathname}${window.location.search}`,
    page_title: document.title,
    ...params,
  };
}

function currentPageType() {
  const params = new URLSearchParams(window.location.search);
  if (params.get("view") === "detail" || params.get("indicator")) return "indicator_detail";
  if (window.location.pathname.startsWith("/blog")) return "blog";
  if (window.location.pathname.startsWith("/legacy")) return "legacy";
  return "atlas";
}

createRoot(document.getElementById("root")).render(<App />);
