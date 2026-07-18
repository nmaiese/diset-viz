import React, { useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import * as d3 from "d3";
import {
  AlertTriangle,
  ArrowDownRight,
  ArrowLeft,
  ArrowLeftRight,
  ArrowUpRight,
  BarChart3,
  Check,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Clock3,
  Layers,
  LineChart,
  MapPinned,
  Minus,
  Search,
  TrendingDown,
  TrendingUp,
  Trophy,
  Users,
  X,
} from "lucide-react";
import "./styles.css";

const API = {
  catalog: "/api/catalog",
  indicator: (id) => `/api/indicator/${encodeURIComponent(id)}`,
  region: (key) => `/api/region/${key}`,
  regionsOverview: "/api/regions/overview",
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
  { id: "az", label: "A-Z" },
  { id: "theme", label: "Tema" },
];

const MAP_RAMP = (t) => d3.interpolate("#E7ECF3", "#15233B")(t);
const MISSING_FILL = "#E2E0D8";

function App() {
  const [catalog, setCatalog] = useState(null);
  const [mapData, setMapData] = useState(null);
  const [indicator, setIndicator] = useState(null);
  const [regionsOverview, setRegionsOverview] = useState(null);
  const [regionProfile, setRegionProfile] = useState(null);
  const [error, setError] = useState(null);

  const [view, setView] = useUrlState("view");
  const [selectedId, setSelectedId] = useUrlState("indicator");
  const [selectedYear, setSelectedYear] = useUrlState("year");
  const [selectedRegion, setSelectedRegion] = useUrlState("region");
  const [regionKey, setRegionKey] = useUrlState("rk");
  const [fromParam, setFromParam] = useUrlState("from");
  const [themeParam, setThemeParam] = useUrlState("theme");
  const [queryParam, setQueryParam] = useUrlState("q");
  const [sortParam, setSortParam] = useUrlState("sort");
  const [partialParam, setPartialParam] = useUrlState("partial");
  const [areaParam, setAreaParam] = useUrlState("area");
  const [sourceParam, setSourceParam] = useUrlState("source");
  const [yearFromParam, setYearFromParam] = useUrlState("yfrom");
  const [yearToParam, setYearToParam] = useUrlState("yto");

  const theme = themeParam || "Tutti";
  const query = queryParam || "";
  const sort = sortParam || "complete";
  const showPartial = partialParam === "1";
  const macroArea = areaParam || "Tutte";
  const sourceFamily = sourceParam || "all";
  // Default to atlas, but a shared ?indicator=… link (no explicit view) opens the detail.
  const activeView =
    view === "detail"
      ? "detail"
      : view === "regioni"
      ? "regioni"
      : view === "confronto"
      ? "confronto"
      : view === "atlas"
      ? "atlas"
      : selectedId
      ? "detail"
      : "atlas";

  const [activeTab, setActiveTab] = useState("map");
  const pageViewKey = activeView === "detail" ? `detail:${selectedId || ""}` : activeView;
  const lastPageViewKey = useRef(null);

  useEffect(() => {
    Promise.all([fetchJson(API.catalog), fetchJson(API.map)])
      .then(([catalogData, geo]) => {
        setCatalog(catalogData);
        setMapData(geo);
      })
      .catch(() => setError("Non è stato possibile caricare l'archivio degli indicatori."));
  }, []);

  // Il boot-loader (app.html) copre la pagina SEO finche' non c'e' davvero
  // qualcosa da mostrare: lo rimuoviamo solo qui, non al mount, altrimenti
  // l'utente vedrebbe comunque il passaggio pagina SEO -> scheletro.
  useEffect(() => {
    if ((catalog && mapData) || error) {
      document.getElementById("boot-loader")?.remove();
    }
  }, [catalog, mapData, error]);

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

  // Region standing map: load once, the first time the region mode is opened.
  useEffect(() => {
    if (activeView !== "regioni" || regionsOverview) return;
    fetchJson(API.regionsOverview)
      .then(setRegionsOverview)
      .catch(() => {});
  }, [activeView, regionsOverview]);

  // A bare ?view=regioni should open an actual regional profile, not a blank
  // chooser. Keep it random so the entry point feels alive without inventing a
  // best/worst ranking.
  useEffect(() => {
    if (activeView !== "regioni" || regionKey || !regionsOverview) return;
    const keys = Object.keys(regionsOverview);
    if (!keys.length) return;
    setRegionKey(keys[Math.floor(Math.random() * keys.length)]);
  }, [activeView, regionKey, regionsOverview]);

  // Selected region profile, refetched whenever the region key changes.
  useEffect(() => {
    if (activeView !== "regioni" || !regionKey) {
      setRegionProfile(null);
      return;
    }
    if (regionProfile && regionProfile.region_key === regionKey) return;
    let cancelled = false;
    fetchJson(API.region(regionKey))
      .then((payload) => {
        if (!cancelled) setRegionProfile(payload);
      })
      .catch(() => {
        if (!cancelled) setRegionProfile(null);
      });
    return () => {
      cancelled = true;
    };
  }, [activeView, regionKey]);

  // Open an indicator's dashboard. `origin` optionally carries the region the user
  // came from, so the dashboard opens on that region and Back can return to it.
  const openIndicator = (item, origin) => {
    setSelectedId(item.id);
    setThemeParam(item.theme);
    setQueryParam(null);
    if (origin && origin.type === "regione" && origin.key) {
      setFromParam(`regione:${origin.key}`);
      if (origin.name) setSelectedRegion(origin.name);
    } else {
      setFromParam(null);
    }
    setView("detail");
    trackEvent("select_indicator", {
      indicator_id: item.id,
      indicator_name: item.name,
      indicator_theme: item.theme,
      from: origin?.type || "atlas",
    });
    window.scrollTo({ top: 0, behavior: "auto" });
  };

  // Back out of the dashboard: return to the region we came from, if any.
  const backFromDetail = () => {
    if (fromParam && fromParam.indexOf("regione:") === 0) {
      const key = fromParam.slice("regione:".length);
      setFromParam(null);
      setRegionKey(key);
      setView("regioni");
    } else {
      setFromParam(null);
      setView("atlas");
    }
    trackEvent("back_from_detail", { to: fromParam || "atlas" });
    window.scrollTo({ top: 0, behavior: "auto" });
  };

  // Switch between reading modes ("per indicatore" / "per regione" / "confronta").
  const goToMode = (mode) => {
    setFromParam(null);
    setView(mode === "regioni" ? "regioni" : mode === "confronto" ? "confronto" : "atlas");
    trackEvent("switch_mode", { mode });
    window.scrollTo({ top: 0, behavior: "auto" });
  };

  // Open a region's profile inside the SPA (from the map, the list, similar
  // regions, or the indicator dashboard) without a full page reload.
  const openRegion = (key) => {
    setFromParam(null);
    setRegionKey(key);
    setView("regioni");
    trackEvent("open_region", { region_key: key });
    window.scrollTo({ top: 0, behavior: "auto" });
  };

  // Select another region while already inside the region workspace. This keeps
  // the page position stable; RegionView resets only the profile panel scroll.
  const selectRegion = (key) => {
    setFromParam(null);
    setRegionKey(key);
    setView("regioni");
    trackEvent("select_region", { region_key: key });
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
        <AtlasViewSkeleton />
        <SiteFooter />
      </main>
    );
  }

  if (activeView === "regioni") {
    return (
      <RegionView
        mapData={mapData}
        overview={regionsOverview}
        regionKey={regionKey}
        profile={regionProfile}
        onSelectRegion={selectRegion}
        onClearRegion={() => setRegionKey(null)}
        onMode={goToMode}
        onOpenIndicator={(item) =>
          openIndicator(item, { type: "regione", key: regionKey, name: regionProfile?.region })
        }
      />
    );
  }

  if (activeView === "confronto") {
    return (
      <CompareView
        catalog={catalog}
        mapData={mapData}
        onMode={goToMode}
        onOpenRegion={openRegion}
      />
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
        onOpenRegion={openRegion}
        onNavRegioni={() => goToMode("regioni")}
        onNavAtlas={() => goToMode("atlas")}
        onBack={backFromDetail}
        backContext={fromParam && fromParam.indexOf("regione:") === 0
          ? { type: "regione", key: fromParam.slice("regione:".length), name: selectedRegion }
          : null}
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
      mapData={mapData}
      onOpenRegion={openRegion}
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
      sourceFamily={sourceFamily}
      setSourceFamily={(value) => {
        setSourceParam(value === "all" ? null : value);
        setThemeParam(null);
        trackEvent("filter_data_source", { source_family: value });
      }}
      yearFrom={yearFromParam ? Number(yearFromParam) : null}
      yearTo={yearToParam ? Number(yearToParam) : null}
      setYearRange={(from, to) => {
        setYearFromParam(from === null ? null : String(from));
        setYearToParam(to === null ? null : String(to));
        trackEvent("filter_year_range", { year_from: from, year_to: to });
      }}
      onOpen={openIndicator}
      onMode={goToMode}
    />
  );
}

/* ------------------------------------------------------------------ */
/* Shared chrome                                                       */
/* ------------------------------------------------------------------ */

function SiteHeader({ children, onNavRegioni, onNavAtlas, activeNav }) {
  const handleLocalNav = (event, handler) => {
    if (handler && !event.metaKey && !event.ctrlKey && event.button === 0) {
      event.preventDefault();
      handler();
    }
  };

  return (
    <>
      <header className="masthead">
        <a className="brand" href="/" aria-label="Divario Italia, home">
          <img className="brand-mark" src="/static/img/logo-mark.png" alt="" width="38" height="38" />
          <span className="brand-text">
            <strong>Divario Italia</strong>
            <small>Atlante degli indicatori territoriali</small>
          </span>
        </a>
        {children}
        <nav id="masthead-nav" className="masthead__links" aria-label="Collegamenti">
          <a
            href="/"
            className={activeNav === "atlas" ? "is-active" : ""}
            onClick={(event) => handleLocalNav(event, onNavAtlas)}
          >
            Atlante
          </a>
          <a
            href="/regioni"
            className={activeNav === "regioni" ? "is-active" : ""}
            onClick={(event) => {
              // Inside the SPA, keep the user in the interactive region mode
              // instead of loading the server page (which stays for SEO/deep links).
              handleLocalNav(event, onNavRegioni);
            }}
          >
            Regioni
          </a>
          <a href="/temi">Temi</a>
          <a href="/qualita-della-vita">Qualità della vita</a>
          <a href="/quiz">Quiz Italia</a>
          <a href="/metodologia">Metodologia</a>
          <a href="/blog">Blog</a>
          <a
            href="https://www.istat.it/sistema-informativo-6/banca-dati-territoriale-per-le-politiche-di-sviluppo/"
            target="_blank"
            rel="noreferrer"
          >
            Fonte Istat <ArrowUpRight size={13} />
          </a>
        </nav>
        <a
          className="masthead__search"
          href="/"
          aria-label="Cerca nell'atlante"
          onClick={(event) => handleLocalNav(event, onNavAtlas)}
        >
          <Search size={18} />
        </a>
      </header>

      <nav className="tabbar" aria-label="Navigazione principale">
        <a
          href="/"
          className={activeNav === "atlas" ? "tabbar__item is-active" : "tabbar__item"}
          onClick={(event) => handleLocalNav(event, onNavAtlas)}
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true"><circle cx="12" cy="12" r="10"></circle><path d="m16.24 7.76-2.12 6.36-6.36 2.12 2.12-6.36z"></path></svg>
          <span>Atlante</span>
        </a>
        <a
          href="/regioni"
          className={activeNav === "regioni" ? "tabbar__item is-active" : "tabbar__item"}
          onClick={(event) => handleLocalNav(event, onNavRegioni)}
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true"><path d="M12 21s7-7.58 7-12A7 7 0 0 0 5 9c0 4.42 7 12 7 12z"></path><circle cx="12" cy="9" r="2.5"></circle></svg>
          <span>Regioni</span>
        </a>
        <a href="/qualita-della-vita" className="tabbar__item">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true"><path d="M22 12h-4l-3 9L9 3l-3 9H2"></path></svg>
          <span>Qualità</span>
        </a>
        <a href="/quiz" className="tabbar__item">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true"><rect x="4" y="4" width="16" height="16"></rect><circle cx="8" cy="8" r="1"></circle><circle cx="16" cy="8" r="1"></circle><circle cx="12" cy="12" r="1"></circle><circle cx="8" cy="16" r="1"></circle><circle cx="16" cy="16" r="1"></circle></svg>
          <span>Gioco</span>
        </a>
        <a href="/blog" className="tabbar__item">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><path d="M14 2v6h6"></path><path d="M9 13h6"></path><path d="M9 17h6"></path></svg>
          <span>Blog</span>
        </a>
      </nav>
    </>
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
        <a href="/">Atlante</a> · <a href="/regioni">Regioni</a> · <a href="/temi">Temi</a> · <a href="/qualita-della-vita">Qualità della vita</a> · <a href="/quiz">Quiz Italia</a> · <a href="/metodologia">Metodologia</a> · <a href="/blog">Blog</a> · <a href="/privacy">Privacy e cookie</a>
      </span>
      {hasConsentPreferences && (
        <button className="privacy-settings-link" type="button" onClick={() => window.diOpenConsentPreferences()}>
          Gestisci preferenze cookie
        </button>
      )}
    </footer>
  );
}

// Top-level reading mode: browse indicators, or look up how a region is doing.
function ModeSwitch({ active, onMode }) {
  const modes = [
    { id: "atlas", label: "Per indicatore", icon: BarChart3 },
    { id: "regioni", label: "Per regione", icon: MapPinned },
    { id: "confronto", label: "Confronta", icon: ArrowLeftRight },
  ];
  return (
    <div className="mode-switch" role="tablist" aria-label="Modalità di lettura">
      {modes.map((mode) => {
        const Icon = mode.icon;
        const isActive = active === mode.id;
        return (
          <button
            key={mode.id}
            type="button"
            role="tab"
            aria-selected={isActive}
            className={isActive ? "mode-switch__tab is-active" : "mode-switch__tab"}
            onClick={() => !isActive && onMode(mode.id)}
          >
            <Icon size={16} /> {mode.label}
          </button>
        );
      })}
    </div>
  );
}

function ContextBar({ label, crumbs, children }) {
  return (
    <section className="context-bar" aria-label="Contesto">
      <div className="context-bar__path">
        <span className="context-bar__label">{label}</span>
        <nav className="breadcrumb" aria-label="Percorso">
          {crumbs.map((crumb, index) => (
            <React.Fragment key={`${crumb.label}-${index}`}>
              {index > 0 && <span>/</span>}
              {crumb.onClick ? (
                <button type="button" onClick={crumb.onClick}>{crumb.label}</button>
              ) : (
                <span>{crumb.label}</span>
              )}
            </React.Fragment>
          ))}
        </nav>
      </div>
      {children && <div className="context-bar__tools">{children}</div>}
    </section>
  );
}

/* ------------------------------------------------------------------ */
/* Stable numeric primitives                                           */
/* ------------------------------------------------------------------ */

function NumericValue({ value, unit = "", format = formatValue, className }) {
  const text = format(value, unit);
  return (
    <span key={text} className={`numeric-value ${className || ""}`.trim()}>
      {text}
    </span>
  );
}

// Bar that grows with transform, so the visual animation never changes layout.
function Bar({ pct, className = "" }) {
  const target = Math.max(0, Math.min(100, pct || 0));
  return (
    <span className={`di-bar ${className}`.trim()} style={{ "--bar-scale": target / 100 }}>
      <i />
    </span>
  );
}

/* ------------------------------------------------------------------ */
/* Home hero: interactive map + dual entry                            */
/* ------------------------------------------------------------------ */

// A short, varied set of indicators to offer in the hero map picker: the
// catalog's featured indicator plus one complete indicator per additional
// theme, capped so the <select> stays scannable (the full 538-item catalog
// lives in the index below, this is just an inviting first taste).
function heroIndicatorChoices(catalog) {
  const seenThemes = new Set();
  const picks = [];
  const featured = catalog.indicators.find((i) => i.id === catalog.featured_indicator_id);
  if (featured) {
    picks.push(featured);
    seenThemes.add(featured.theme);
  }
  for (const item of catalog.indicators) {
    if (picks.length >= 6) break;
    if (!item.complete || seenThemes.has(item.theme)) continue;
    picks.push(item);
    seenThemes.add(item.theme);
  }
  return picks;
}

function HomeMapHero({ catalog, mapData, onOpenRegion }) {
  const choices = useMemo(() => heroIndicatorChoices(catalog), [catalog]);
  const [heroIndId, setHeroIndId] = useState(choices[0]?.id ?? catalog.featured_indicator_id);
  const [heroIndicator, setHeroIndicator] = useState(null);
  const [hoverRow, setHoverRow] = useState(null);

  useEffect(() => {
    let cancelled = false;
    fetchJson(API.indicator(heroIndId))
      .then((payload) => { if (!cancelled) setHeroIndicator(payload); })
      .catch(() => {});
    return () => { cancelled = true; };
  }, [heroIndId]);

  const meta = heroIndicator?.metadata;
  const year = meta?.year_max;
  const values = useMemo(
    () => (heroIndicator ? valuesForYear(heroIndicator.series, year) : []),
    [heroIndicator, year],
  );
  // ItalyMap's onSelect/onHover hand back the region's display name (row.region);
  // navigation needs the region_key slug, so look it up from the same rows.
  const handleMapSelect = (name) => {
    const row = values.find((entry) => entry.region === name);
    if (row) onOpenRegion(row.region_key);
  };

  return (
    <section className="home-hero">
      <div className="home-hero__intro">
        <p className="eyebrow">Istat · {catalog.indicators.length} indicatori · 20 regioni · {coverageSpan(catalog)}</p>
        <h1>
          Un atlante per leggere l'Italia,<br />
          regione per regione.
        </h1>
        <p className="atlas-hero__lead">
          Indicatori territoriali e BES Istat per capire dove l'Italia corre e dove resta indietro.
          Filtra per area, tema o anni, poi apri la scheda di ogni indicatore con mappa,
          classifica e andamento nel tempo.
        </p>
        <div className="entry-cards">
          <a className="entry-card" href="#home-map">
            <span className="entry-card__icon"><MapPinned size={20} /></span>
            <strong>Parti da una regione</strong>
            <span>Clicca una regione sulla mappa per aprirne il profilo.</span>
            <span className="entry-card__go">Esplora la mappa ↓</span>
          </a>
          <a className="entry-card" href="#atlas-index">
            <span className="entry-card__icon"><Layers size={20} /></span>
            <strong>Parti da un tema</strong>
            <span>Sfoglia gli indicatori per area e completezza.</span>
            <span className="entry-card__go">Vai all'indice ↓</span>
          </a>
        </div>
      </div>

      <div className="map-panel" id="home-map">
        <div className="map-panel__bar">
          <span className="lbl">Colora la mappa per</span>
          <select
            className="map-panel__select"
            value={heroIndId}
            onChange={(event) => setHeroIndId(Number(event.target.value))}
            aria-label="Indicatore mostrato sulla mappa"
          >
            {choices.map((item) => (
              <option key={item.id} value={item.id}>{item.name}</option>
            ))}
          </select>
          {year != null && <span className="lbl map-panel__year">{year}</span>}
        </div>
        <div className="map-panel__body">
          {heroIndicator && meta ? (
            <>
              <ItalyMap
                geo={mapData}
                values={values}
                selectedRegion={hoverRow?.region}
                onSelect={handleMapSelect}
                onHover={setHoverRow}
                unit={meta.unit}
              />
              <div className="map-readout">
                {hoverRow ? (
                  <>
                    <span className="map-readout__name">{hoverRow.region}</span>
                    <span className="map-readout__value">{formatValue(hoverRow.value, meta.unit)}</span>
                    <span className="map-readout__go">Clicca per il profilo →</span>
                  </>
                ) : (
                  <span className="map-readout__hint">
                    Passa sopra una regione per vederne il valore. Clicca per aprire il profilo completo.
                  </span>
                )}
              </div>
            </>
          ) : (
            <p className="map-empty">Caricamento mappa...</p>
          )}
        </div>
      </div>
    </section>
  );
}

/* ------------------------------------------------------------------ */
/* Atlas (browse) view                                                */
/* ------------------------------------------------------------------ */

function AtlasView({
  catalog, mapData, onOpenRegion, theme, setTheme, query, setQuery, sort, setSort, showPartial, setShowPartial,
  macroArea, setMacroArea, sourceFamily, setSourceFamily, yearFrom, yearTo, setYearRange, onOpen, onMode,
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
    if (sourceFamily !== "all") list = list.filter((i) => i.catalog_family === sourceFamily);
    if (macroArea !== "Tutte") list = list.filter((i) => i.macro_area === macroArea);
    // Year coverage: only the bounds the user actually set constrain the list.
    // "Dal X" keeps series that reach back to X; "Al Y" keeps series that run up to Y.
    if (yearFrom != null) list = list.filter((i) => i.year_min <= yearFrom);
    if (yearTo != null) list = list.filter((i) => i.year_max >= yearTo);
    return list;
  }, [catalog, showPartial, sourceFamily, macroArea, yearFrom, yearTo]);

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
      list = list.filter((i) => normalizeText(
        `${i.name} ${i.theme} ${i.source_theme || ""} ${i.archive} ${i.catalog_family_label}`,
      ).includes(nq));
    }
    return [...list].sort(SORTERS[sort] || SORTERS.complete);
  }, [pool, theme, query, sort]);

  const completeTotal = useMemo(() => catalog.indicators.filter((i) => (
    i.complete
    && (sourceFamily === "all" || i.catalog_family === sourceFamily)
    && (macroArea === "Tutte" || i.macro_area === macroArea)
  )).length, [catalog, sourceFamily, macroArea]);

  return (
    <main className="app-shell">
      <SiteHeader
        activeNav="atlas"
        onNavAtlas={() => onMode("atlas")}
        onNavRegioni={() => onMode("regioni")}
      />

      <ContextBar label="Atlante" crumbs={[{ label: "Atlante" }]}>
        <ModeSwitch active="atlas" onMode={onMode} />
      </ContextBar>

      <HomeMapHero catalog={catalog} mapData={mapData} onOpenRegion={onOpenRegion} />

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

        <div className="index-panel" id="atlas-index">
          <CommandBar
            query={query}
            setQuery={setQuery}
            sort={sort}
            setSort={setSort}
            showPartial={showPartial}
            setShowPartial={setShowPartial}
            sourceFamilies={catalog.source_families || []}
            sourceFamily={sourceFamily}
            setSourceFamily={setSourceFamily}
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
  sourceFamilies, sourceFamily, setSourceFamily,
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
          placeholder="Cerca turismo, occupazione, rifiuti, banda larga"
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
          <span>Fonte dati</span>
          <select value={sourceFamily} onChange={(event) => setSourceFamily(event.target.value)}>
            <option value="all">Tutte</option>
            {sourceFamilies.map((source) => (
              <option key={source.id} value={source.id}>{source.label}</option>
            ))}
          </select>
          <ChevronDown className="select-icon" size={15} />
        </label>
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
          <small className="index-row__theme">
            {item.theme}{item.source_theme && item.source_theme !== item.theme ? ` · ${item.source_theme}` : ""} · {item.catalog_family_label}
          </small>
          <strong className="index-row__name">{item.name}</strong>
          {item.explain?.plain && (
            <span className="index-row__description">{item.explain.plain}</span>
          )}
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
      <span className="coverage__pill">{item.year_min}-{item.year_max}</span>
      {item.complete ? (
        <span className="coverage__pill is-complete"><Check size={12} /> completo</span>
      ) : (
        <span className="coverage__pill is-partial">{Math.round(item.completeness * 100)}% dati</span>
      )}
      {item.quality_life_scored && (
        <span className="coverage__pill is-quality">Qualità della vita</span>
      )}
    </span>
  );
}

/* ------------------------------------------------------------------ */
/* Region (per-region) view                                           */
/* ------------------------------------------------------------------ */

function RegionView({
  mapData, overview, regionKey, profile, onSelectRegion, onClearRegion, onMode, onOpenIndicator,
}) {
  const entries = useMemo(() => (overview ? Object.values(overview) : []), [overview]);
  const values = useMemo(
    () => entries.map((entry) => ({ region: entry.region, region_key: entry.region_key, value: null })),
    [entries],
  );
  const selectedEntry = overview && regionKey ? overview[regionKey] : null;
  const selectedName = selectedEntry?.region || profile?.region || null;
  const profileReady = profile && profile.region_key === regionKey;

  const handleMapSelect = (name) => {
    const found = entries.find((entry) => entry.region === name);
    if (found) onSelectRegion(found.region_key);
  };

  const selectRandomRegion = () => {
    if (!entries.length) return;
    const candidates = entries.filter((entry) => entry.region_key !== regionKey);
    const pool = candidates.length ? candidates : entries;
    onSelectRegion(pool[Math.floor(Math.random() * pool.length)].region_key);
  };

  return (
    <main className="app-shell">
      <SiteHeader
        activeNav="regioni"
        onNavAtlas={() => onMode("atlas")}
        onNavRegioni={selectRandomRegion}
      >
        {selectedName && (
          <button className="back-link" type="button" onClick={selectRandomRegion}>
            <MapPinned size={16} /> Regione casuale
          </button>
        )}
      </SiteHeader>

      <ContextBar
        label="Per regione"
        crumbs={[
          { label: "Atlante", onClick: () => onMode("atlas") },
          { label: "Per regione" },
          ...(selectedName ? [{ label: selectedName }] : []),
        ]}
      >
        <ModeSwitch active="regioni" onMode={onMode} />
      </ContextBar>

      <section className="atlas-hero atlas-hero--compact atlas-hero--region">
        <p className="eyebrow">Istat · 20 regioni · profili territoriali</p>
        <h1>Come è messa ogni regione.</h1>
        <p className="atlas-hero__lead">
          Scegli una regione sulla mappa o dal menu: trovi i temi in cui emerge, quelli in cui
          fatica, gli indicatori collegati e i movimenti dell'ultimo anno. La classifica sintetica
          resta nella sezione Qualità della vita.
        </p>
      </section>

      <section className="region-explore">
        <aside className="region-select">
          <div className="region-select__head">
            <h2>Scegli una regione</h2>
            <p>La mappa serve per navigare tra le schede regionali, senza ordinare i territori in una graduatoria unica.</p>
          </div>
          {overview ? (
            <>
              <div className="region-map">
                <ItalyMap
                  geo={mapData}
                  values={values}
                  selectedRegion={selectedName}
                  onSelect={handleMapSelect}
                  unit=""
                  neutral
                />
              </div>
              <label className="region-switcher">
                <span className="lbl">Cambia regione</span>
                <select value={regionKey || ""} onChange={(event) => onSelectRegion(event.target.value)}>
                  {!regionKey && <option value="" disabled>Scegli...</option>}
                  {entries.map((entry) => (
                    <option key={entry.region_key} value={entry.region_key}>{entry.region}</option>
                  ))}
                </select>
              </label>
            </>
          ) : (
            <LoadingState />
          )}
        </aside>

        <div className="region-profile-panel">
          {!regionKey ? (
            <RegionIntro />
          ) : !profileReady ? (
            <RegionProfileSkeleton name={selectedName} />
          ) : (
            <RegionProfile
              profile={profile}
              onOpenIndicator={onOpenIndicator}
              onSelectRegion={onSelectRegion}
              onRandomRegion={selectRandomRegion}
            />
          )}
        </div>
      </section>
      <SiteFooter />
    </main>
  );
}

function RegionProfileSkeleton({ name }) {
  return (
    <article className="region-profile region-profile--loading" aria-busy="true">
      <header className="region-profile__head">
        <h2>{name || "Regione"}</h2>
        <p className="region-profile__meta">Carico il profilo di {name || "questa regione"}...</p>
      </header>
      <div className="skel-bars" aria-hidden="true"><span /><span /><span /></div>
    </article>
  );
}

function RegionIntro() {
  return (
    <div className="region-intro">
      <header className="region-intro__head">
        <MapPinned size={30} />
        <div>
          <h2>Scelgo una regione</h2>
          <p>
            L'atlante sta aprendo una scheda regionale casuale. Da lì puoi passare alle altre
            regioni con la mappa o con il menu.
          </p>
        </div>
      </header>
      <p className="region-intro__loading">Carico le regioni...</p>
    </div>
  );
}

function RegionProfile({ profile, onOpenIndicator, onSelectRegion, onRandomRegion }) {
  const moves = [...profile.movement_gains, ...profile.movement_losses];
  const moveMax = Math.max(1, ...moves.map((m) => Math.abs(m.movement)));

  // Which theme rows are expanded in the "Tutti i temi" accordion.
  const [expanded, setExpanded] = useState(() => new Set());
  const toggleTheme = (name) =>
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  // Every core indicator of the region, grouped by theme, to reveal on expand.
  const indicatorsByTheme = useMemo(() => {
    const map = new Map();
    for (const ind of profile.all_indicators || []) {
      if (!map.has(ind.theme)) map.set(ind.theme, []);
      map.get(ind.theme).push(ind);
    }
    return map;
  }, [profile]);

  const themesRef = useRef(null);
  const openThemeAndScroll = (name) => {
    setExpanded((prev) => new Set(prev).add(name));
    requestAnimationFrame(() => themesRef.current?.scrollIntoView({ behavior: "auto", block: "nearest" }));
  };

  const topStrong = profile.themes_strong[0];
  const topWeak = profile.themes_weak[0];
  const topGain = profile.movement_gains[0];
  const topLoss = profile.movement_losses[0];

  return (
    <article className="region-profile">
      <header className="region-profile__head">
        <button type="button" className="region-profile__back" onClick={onRandomRegion}>
          <MapPinned size={15} /> Regione casuale
        </button>
        <h2>{profile.region}</h2>
        <p className="region-profile__meta">
          Profilo costruito su {profile.scored_count} indicatori Istat con una direzione chiara,
          più gli indicatori contestuali utili a leggere il territorio.
        </p>
        <div className="region-summary">
          {topStrong && (
            <button type="button" className="region-summary__item is-strong" onClick={() => openThemeAndScroll(topStrong.theme)}>
              <small><TrendingUp size={12} /> Forte in</small>
              <strong>{topStrong.theme}</strong>
            </button>
          )}
          {topWeak && (
            <button type="button" className="region-summary__item is-weak" onClick={() => openThemeAndScroll(topWeak.theme)}>
              <small><TrendingDown size={12} /> Debole in</small>
              <strong>{topWeak.theme}</strong>
            </button>
          )}
          {(topGain || topLoss) && (
            <button
              type="button"
              className="region-summary__item"
              onClick={() => onOpenIndicator((topGain || topLoss))}
            >
              <small>Si muove di più</small>
              <strong>{(topGain || topLoss).name}</strong>
              <b className={topGain ? "is-up" : "is-down"}>
                {topGain ? `+${topGain.movement}` : topLoss.movement}
              </b>
            </button>
          )}
        </div>
      </header>

      <div className="region-cols">
        <section className="region-card region-card--strong">
          <h3><TrendingUp size={16} /> Dove eccelle</h3>
          {profile.themes_strong.length ? (
            <ThemeScoreList items={profile.themes_strong} />
          ) : (
            <p className="card-empty">Nessun tema emerge nettamente sopra la media.</p>
          )}
          {!!profile.top_excels.length && (
            <IndicatorLinkList items={profile.top_excels} onOpen={onOpenIndicator} />
          )}
        </section>
        <section className="region-card region-card--weak">
          <h3><TrendingDown size={16} /> Dove resta indietro</h3>
          {profile.themes_weak.length ? (
            <ThemeScoreList items={profile.themes_weak} />
          ) : (
            <p className="card-empty">Nessun tema emerge nettamente sotto la media.</p>
          )}
          {!!profile.top_lags.length && (
            <IndicatorLinkList items={profile.top_lags} onOpen={onOpenIndicator} />
          )}
        </section>
      </div>

      {moves.length > 0 && (
        <section className="region-card">
          <h3>Il movimento dell'ultimo anno</h3>
          <p className="region-card__note">
            Posizioni guadagnate o perse rispetto alle altre regioni fra l'ultimo anno disponibile
            e quello comparabile precedente.
          </p>
          <div className="region-cols">
            <div className="region-move-col">
              <h4 className="is-up">Dove recupera</h4>
              <MovementList items={profile.movement_gains} moveMax={moveMax} dir="up" onOpen={onOpenIndicator} />
            </div>
            <div className="region-move-col">
              <h4 className="is-down">Dove perde</h4>
              <MovementList items={profile.movement_losses} moveMax={moveMax} dir="down" onOpen={onOpenIndicator} />
            </div>
          </div>
        </section>
      )}

      <section className="region-card" ref={themesRef}>
        <h3><Layers size={16} /> Tutti i temi</h3>
        <p className="region-card__note">
          Clicca un tema per aprire i suoi indicatori con valore, posizione tra le 20 regioni e
          movimento recente.
        </p>
        <div className="theme-accordion">
          {profile.theme_table.map((t, idx) => {
            const inds = indicatorsByTheme.get(t.theme) || [];
            const isOpen = expanded.has(t.theme);
            const panelId = `theme-panel-${idx}`;
            return (
              <div key={t.theme} className={`theme-acc${isOpen ? " is-open" : ""}${t.rated ? "" : " is-unrated"}`}>
                <button
                  type="button"
                  className="theme-acc__head"
                  aria-expanded={isOpen}
                  aria-controls={panelId}
                  onClick={() => toggleTheme(t.theme)}
                  disabled={!inds.length}
                >
                  <ChevronRight className="theme-acc__caret" size={16} />
                  <span className="theme-acc__name">{t.theme}<em>{t.count} ind.</em></span>
                </button>
                {isOpen && (
                  <div className="theme-acc__panel" id={panelId}>
                    <ul className="region-ind-rows">
                      {inds.map((ind) => (
                        <li key={ind.id}>
                          <button type="button" className="region-ind-row" onClick={() => onOpenIndicator(ind)}>
                            <span className="region-ind-row__name">{ind.name}</span>
                            <span className="region-ind-row__value">{formatValue(ind.value, ind.unit)}</span>
                            <span className="region-ind-row__rank">
                              {ind.rank ? <><b>{ind.rank}</b><small>/{ind.region_count}</small></> : <small>n.v.</small>}
                            </span>
                            <span className="region-ind-row__move">
                              {ind.movement ? (
                                <em className={ind.movement > 0 ? "is-up" : "is-down"}>
                                  {ind.movement > 0 ? `+${ind.movement}` : ind.movement}
                                </em>
                              ) : (
                                <small>=</small>
                              )}
                            </span>
                            <ChevronRight className="region-ind-row__chev" size={14} />
                          </button>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </section>

      {!!profile.similar_regions.length && (
        <section className="region-card region-similar">
          <h3><Users size={16} /> Regioni con un profilo simile</h3>
          <div className="region-similar__grid">
            {profile.similar_regions.map((s) => (
              <button
                key={s.region_key}
                type="button"
                className="region-similar__card"
                onClick={() => onSelectRegion(s.region_key)}
              >
                {s.region}
              </button>
            ))}
          </div>
        </section>
      )}

      <a className="region-cta" href={`/regione/${profile.region_key}`}>
        <span>
          <small>Scheda completa</small>
          <strong>Apri la pagina dettagliata e stampabile di {profile.region}</strong>
        </span>
        <ArrowUpRight size={18} />
      </a>
    </article>
  );
}

function ThemeScoreList({ items }) {
  return (
    <ul className="theme-chip-list">
      {items.map((t) => (
        <li key={t.theme}>
          <span className="theme-chip-list__name">{t.theme}</span>
        </li>
      ))}
    </ul>
  );
}

function IndicatorLinkList({ items, onOpen }) {
  return (
    <ul className="region-ind-list">
      {items.map((e) => (
        <li key={e.id}>
          <button type="button" onClick={() => onOpen(e)}>
            <span className="region-ind-list__label">
              {e.name}<small>{e.theme}</small>
            </span>
            <ChevronRight size={15} />
          </button>
        </li>
      ))}
    </ul>
  );
}

function MovementList({ items, moveMax, dir, onOpen }) {
  if (!items.length) {
    return <p className="card-empty">{dir === "up" ? "Nessun recupero netto." : "Nessuna perdita netta."}</p>;
  }
  return (
    <ul className="region-move-list">
      {items.map((m) => (
        <li key={m.id}>
          <button type="button" onClick={() => onOpen(m)}>
            <span className="region-move-list__head">
              <span className="region-move-list__name">{m.name}</span>
              <em className={dir === "up" ? "is-up" : "is-down"}>
                {m.movement > 0 ? `+${m.movement}` : m.movement}
              </em>
            </span>
            <Bar pct={(Math.abs(m.movement) / moveMax) * 100} className={dir === "up" ? "di-bar--up" : "di-bar--down"} />
            <small>{m.theme} · {m.year_from}-{m.year}</small>
          </button>
        </li>
      ))}
    </ul>
  );
}

/* ------------------------------------------------------------------ */
/* Compare (multi-region) view                                        */
/* ------------------------------------------------------------------ */

const COMPARE_SERIES_COLORS = ["var(--accent)", "var(--ink)", "var(--positive)"];
const COMPARE_MAX_REGIONS = 3;

function CompareTimeline({ seriesList, averageSeries, selectedYear, onYear, unit }) {
  const width = 720;
  const height = 300;
  const margin = { top: 20, right: 24, bottom: 34, left: 58 };
  const all = [...seriesList.flatMap((s) => s.points), ...averageSeries].filter((row) => Number.isFinite(row.value));
  if (!all.length) return <p className="card-empty">Serie storica non disponibile.</p>;

  const x = d3.scaleLinear().domain(d3.extent(all, (row) => row.year)).range([margin.left, width - margin.right]);
  const y = d3.scaleLinear().domain(d3.extent(all, (row) => row.value)).nice().range([height - margin.bottom, margin.top]);
  const line = d3.line().defined((row) => Number.isFinite(row.value)).x((row) => x(row.year)).y((row) => y(row.value)).curve(d3.curveMonotoneX);

  return (
    <svg className="timeline" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Serie storica a confronto">
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
      {seriesList.map((s) => <path key={s.region} d={line(s.points)} style={{ stroke: s.color }} className="compare-line" />)}
      {seriesList.map((s) => {
        const pt = s.points.find((row) => row.year === selectedYear) || s.points[s.points.length - 1];
        return pt && Number.isFinite(pt.value) ? (
          <circle
            key={s.region}
            cx={x(pt.year)}
            cy={y(pt.value)}
            r={5}
            style={{ fill: s.color }}
            tabIndex={0}
            role="button"
            onClick={() => onYear(pt.year)}
            onKeyDown={(event) => {
              if (event.key === "Enter" || event.key === " ") { event.preventDefault(); onYear(pt.year); }
            }}
          >
            <title>{s.region}, {pt.year}: {formatValue(pt.value, unit)}</title>
          </circle>
        ) : null;
      })}
      <g className="x-axis">
        {x.ticks(6).map((tick) => (
          <text
            key={tick}
            x={x(tick)}
            y={height - 10}
            className={Math.round(tick) === selectedYear ? "is-active" : ""}
            onClick={() => onYear(Math.round(tick))}
          >
            {Math.round(tick)}
          </text>
        ))}
      </g>
    </svg>
  );
}

function CompareView({ catalog, mapData, onMode, onOpenRegion }) {
  const [indId, setIndId] = useState(catalog.featured_indicator_id);
  const [indicator, setIndicator] = useState(null);
  const [regionNames, setRegionNames] = useState([]);
  const [year, setYear] = useState(null);

  useEffect(() => {
    let cancelled = false;
    fetchJson(API.indicator(indId))
      .then((payload) => {
        if (cancelled) return;
        setIndicator(payload);
        setYear(payload.metadata.year_max);
        setRegionNames((current) => {
          const valid = current.filter((name) => payload.metadata.regions.includes(name));
          if (valid.length) return valid;
          return payload.metadata.regions.slice(0, 3);
        });
      })
      .catch(() => {});
    return () => { cancelled = true; };
  }, [indId]);

  const meta = indicator?.metadata;
  const series = indicator?.series || [];
  const yearValues = useMemo(() => (year != null ? valuesForYear(series, year) : []), [series, year]);
  const averageSeries = useMemo(() => buildAverageSeries(series), [series]);
  const seriesList = useMemo(
    () => regionNames.map((name, i) => ({
      region: name,
      color: COMPARE_SERIES_COLORS[i],
      points: valuesForRegion(series, name),
    })),
    [regionNames, series],
  );
  const valueByRegion = useMemo(() => new Map(yearValues.map((row) => [row.region, row])), [yearValues]);
  const nationalAvg = yearValues.length ? yearValues.reduce((sum, row) => sum + row.value, 0) / yearValues.length : null;
  const bestRegion = useMemo(() => {
    if (!regionNames.length) return null;
    return regionNames.reduce((best, name) => {
      const row = valueByRegion.get(name);
      if (!row) return best;
      const bestRow = best ? valueByRegion.get(best) : null;
      if (!bestRow) return name;
      const better = meta?.invert ? row.value < bestRow.value : row.value > bestRow.value;
      return better ? name : best;
    }, null);
  }, [regionNames, valueByRegion, meta]);

  // ItalyMap's onSelect hands back the region's display name; navigation needs
  // the region_key slug, so look it up from the same year's rows.
  const handleMapSelect = (name) => {
    const row = valueByRegion.get(name);
    if (row) onOpenRegion(row.region_key);
  };

  const availableRegions = (meta?.regions || []).filter((name) => !regionNames.includes(name));
  const addRegion = (name) => { if (name && regionNames.length < COMPARE_MAX_REGIONS) setRegionNames([...regionNames, name]); };
  const removeRegion = (name) => { if (regionNames.length > 1) setRegionNames(regionNames.filter((n) => n !== name)); };

  return (
    <main className="app-shell">
      <SiteHeader activeNav="atlas" onNavAtlas={() => onMode("atlas")} onNavRegioni={() => onMode("regioni")} />

      <ContextBar label="Confronta" crumbs={[{ label: "Confronta" }]}>
        <ModeSwitch active="confronto" onMode={onMode} />
      </ContextBar>

      <section className="atlas-hero atlas-hero--compact">
        <p className="eyebrow">Confronto regioni</p>
        <h1>Metti due o tre regioni a confronto.</h1>
        <p className="atlas-hero__lead">
          Scegli un indicatore e fino a tre regioni. Le vedi sovrapposte nella serie storica,
          sulla mappa e in tabella, contro la media nazionale.
        </p>
      </section>

      <div className="compare-bar">
        <label className="compare-select">
          <span className="lbl">Indicatore</span>
          <select value={indId} onChange={(event) => setIndId(Number(event.target.value))}>
            {catalog.indicators.map((item) => (
              <option key={item.id} value={item.id}>{item.name}</option>
            ))}
          </select>
        </label>
        <div className="cmp-chips-field">
          <span className="lbl">Regioni ({regionNames.length}/{COMPARE_MAX_REGIONS})</span>
          <div className="cmp-chips">
            {regionNames.map((name, i) => (
              <span className="cmp-chip" key={name}>
                <span className="cmp-chip__swatch" style={{ background: COMPARE_SERIES_COLORS[i] }} />
                {name}
                {regionNames.length > 1 && (
                  <button type="button" aria-label={`Rimuovi ${name}`} onClick={() => removeRegion(name)}>
                    <X size={13} />
                  </button>
                )}
              </span>
            ))}
            {regionNames.length < COMPARE_MAX_REGIONS && availableRegions.length > 0 && (
              <span className="cmp-chip cmp-chip--add">
                <select value="" onChange={(event) => addRegion(event.target.value)} aria-label="Aggiungi regione">
                  <option value="" disabled>Aggiungi…</option>
                  {availableRegions.map((name) => <option key={name} value={name}>{name}</option>)}
                </select>
              </span>
            )}
          </div>
        </div>
      </div>

      {!meta ? (
        <p className="map-empty">Caricamento…</p>
      ) : (
        <div className="compare-layout">
          <div className="compare-main">
            <DataCard title="Serie storica" kicker={`${meta.name} · ${meta.unit}`}>
              <div className="compare-legend">
                {seriesList.map((s) => <span key={s.region} className="legend-item"><i style={{ background: s.color }} />{s.region}</span>)}
                <span className="legend-item legend-average"><i />Media nazionale</span>
              </div>
              <CompareTimeline seriesList={seriesList} averageSeries={averageSeries} selectedYear={year} onYear={setYear} unit={meta.unit} />
            </DataCard>
            <DataCard title="Mappa" kicker={`${year} · regioni a confronto evidenziate`}>
              <ItalyMap
                geo={mapData}
                values={yearValues}
                selectedRegion={regionNames}
                onSelect={handleMapSelect}
                unit={meta.unit}
              />
            </DataCard>
          </div>
          <aside className="compare-side">
            <DataCard title={`Confronto · ${year}`} kicker={meta.unit}>
              <table className="cmp-table">
                <thead><tr><th>Regione</th><th className="num">Valore</th></tr></thead>
                <tbody>
                  {regionNames.map((name, i) => {
                    const row = valueByRegion.get(name);
                    return (
                      <tr key={name}>
                        <td><span className="cmp-swatch" style={{ background: COMPARE_SERIES_COLORS[i] }} />{name}</td>
                        <td className={`num ${name === bestRegion ? "cmp-winner" : ""}`}>
                          {row ? formatValue(row.value, meta.unit) : "n.d."}
                        </td>
                      </tr>
                    );
                  })}
                  <tr>
                    <td className="cmp-avg-label">Media nazionale</td>
                    <td className="num cmp-avg-label">{nationalAvg != null ? formatValue(nationalAvg, meta.unit) : "n.d."}</td>
                  </tr>
                </tbody>
              </table>
              {bestRegion && (
                <p className="compare-note">
                  Migliore tra le selezionate: <strong>{bestRegion}</strong>
                  {meta.invert ? " (valore più basso è meglio)" : ""}.
                </p>
              )}
            </DataCard>
          </aside>
        </div>
      )}
      <SiteFooter />
    </main>
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
  onOpenRegion,
  onNavRegioni,
  onNavAtlas,
  onBack,
  backContext,
  activeTab,
  setActiveTab,
}) {
  const fromRegion = backContext && backContext.type === "regione" ? backContext : null;
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

  const siblingIndex = siblings.findIndex((item) => String(item.id) === String(selectedId));
  const prev = siblingIndex > 0 ? siblings[siblingIndex - 1] : null;
  const next = siblingIndex >= 0 && siblingIndex < siblings.length - 1 ? siblings[siblingIndex + 1] : null;

  return (
    <main className="app-shell">
      <SiteHeader
        activeNav={fromRegion ? "regioni" : "atlas"}
        onNavAtlas={onNavAtlas}
        onNavRegioni={onNavRegioni}
      >
        <button className="back-link" type="button" onClick={onBack}>
          <ArrowLeft size={16} /> {fromRegion ? fromRegion.name : "Atlante"}
        </button>
      </SiteHeader>

      {!indicatorMeta ? (
        <DetailViewSkeleton />
      ) : (
        <>
          <ContextBar
            label="Scheda indicatore"
            crumbs={
              fromRegion
                ? [
                    { label: "Regioni", onClick: onBack },
                    { label: fromRegion.name, onClick: onBack },
                    { label: indicatorMeta.name },
                  ]
                : [
                    { label: "Atlante", onClick: onBack },
                    { label: indicatorMeta.theme },
                    { label: indicatorMeta.name },
                  ]
            }
          />

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
              <InsightPanel insights={insights} unit={indicatorMeta.unit} year={year} region={selectedRegion} onOpenRegion={onOpenRegion} />
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

function indicatorPath(id, name, path) {
  if (path) return path;
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
      <span className="tag">{metadata.theme} · {metadata.catalog_family_label}</span>
      {metadata.quality_life_scored && (
        <span className="tag tag--quality">Nel punteggio: {metadata.quality_life_category_label}</span>
      )}
      <h2>{metadata.name}</h2>
      <p className="indicator-header__seo">
        <a href={indicatorPath(metadata.id, metadata.name, metadata.path)}>Scheda completa e classifica regioni →</a>
      </p>
      {metadata.explain && <IndicatorExplain explain={metadata.explain} />}
      {/* Definition and metadata are collapsed so the year/region controls and the
          selected-region KPI stay near the top of the panel, in view. */}
      <details className="indicator-header__more">
        <summary>Definizione e dettagli</summary>
        {metadata.archive && (
          <p className="indicator-header__def">
            <small>Definizione</small>
            {metadata.archive}
          </p>
        )}
        <dl>
          {metadata.source_theme && metadata.source_theme !== metadata.theme && (
            <div><dt>Sottotema Istat</dt><dd>{metadata.source_theme}</dd></div>
          )}
          <div><dt>Unità di misura</dt><dd>{metadata.unit || "n.d."}</dd></div>
          <div><dt>Copertura</dt><dd>{metadata.year_min}-{metadata.year_max}</dd></div>
          <div><dt>Regioni</dt><dd>{regionCount || metadata.regions.length}/20</dd></div>
          <div><dt>Fonte</dt><dd>{metadata.source_url ? (<a href={metadata.source_url} target="_blank" rel="noreferrer">{metadata.source_label || metadata.source}</a>) : (metadata.source_label || metadata.source)}</dd></div>
        </dl>
      </details>
    </div>
  );
}

function IndicatorExplain({ explain }) {
  const detailRows = [
    ["In pratica", explain.example],
    ["Perimetro", explain.scope],
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
          <summary>Capisci unità, perimetro e limiti</summary>
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

function InsightPanel({ insights, unit, year, region, onOpenRegion }) {
  const TrendIcon = insights.delta > 0 ? ArrowUpRight : insights.delta < 0 ? ArrowDownRight : Minus;
  const trendClass = insights.delta > 0 ? "is-up" : insights.delta < 0 ? "is-down" : "is-flat";
  return (
    <div className="insights">
      <div className="insight insight--region">
        <small>{region || "Regione"} · {year}</small>
        <strong><NumericValue value={insights.regionEntry?.value} unit={unit} /></strong>
        <span>
          {insights.regionRank
            ? `${insights.regionRank}ª su ${insights.total} regioni`
            : "Dato non disponibile per quest'anno"}
        </span>
        {region && (
          <a
            className="insight__link"
            href={`/regione/${regionKey(region)}`}
            onClick={(event) => {
              // Stay inside the SPA when we can (no reload); the href keeps the
              // link crawlable and works without JS.
              if (onOpenRegion && !event.metaKey && !event.ctrlKey && event.button === 0) {
                event.preventDefault();
                onOpenRegion(regionKey(region));
              }
            }}
          >
            Come è messa {region} →
          </a>
        )}
      </div>
      <div className="insight">
        <small><Trophy size={13} /> Valore più alto · {year}</small>
        <strong>{insights.top?.region || "n.d."}</strong>
        <span><NumericValue value={insights.top?.value} unit={unit} /></span>
      </div>
      <div className="insight">
        <small>Valore più basso · {year}</small>
        <strong>{insights.bottom?.region || "n.d."}</strong>
        <span><NumericValue value={insights.bottom?.value} unit={unit} /></span>
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

function ItalyMap({ geo, values, selectedRegion, onSelect, unit, neutral = false, onHover }) {
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
          const isSelected = Array.isArray(selectedRegion)
            ? row && selectedRegion.includes(row.region)
            : row?.region === selectedRegion;
          const title = row
            ? neutral
              ? row.region
              : `${row.region}: ${formatValue(row.value, unit)}`
            : feature.properties.name;
          return (
            <path
              key={key}
              d={path(feature)}
              className={isSelected ? "is-selected" : ""}
              fill={neutral ? MISSING_FILL : hasValue ? color(row.value) : MISSING_FILL}
              onClick={() => row && onSelect(row.region)}
              onMouseEnter={() => onHover && onHover(row || null)}
              onMouseLeave={() => onHover && onHover(null)}
              tabIndex={0}
              role="button"
              aria-label={title}
              onKeyDown={(event) => {
                if ((event.key === "Enter" || event.key === " ") && row) {
                  event.preventDefault();
                  onSelect(row.region);
                }
              }}
            >
              <title>{title}</title>
            </path>
          );
        })}
      </svg>
      {neutral ? null : hasData ? (
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
          <strong><NumericValue value={row.value} unit={unit} /></strong>
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
      <p>Preparazione degli indicatori territoriali...</p>
    </section>
  );
}

// Riproduce la sagoma di AtlasView (hero + spine + indice) invece del generico
// LoadingState da 320px, per evitare il salto di layout al primo caricamento
// della Home, la pagina più visitata del sito.
function AtlasViewSkeleton() {
  return (
    <>
      <section className="context-bar" aria-label="Contesto" aria-hidden="true">
        <div className="context-bar__path">
          <span className="skel-bar" style={{ height: 14, width: 120 }} />
        </div>
      </section>
      <section className="atlas-hero" aria-hidden="true">
        <div className="skel-bars" style={{ marginTop: 0 }}>
          <span style={{ height: 14, width: "35%" }} />
          <span style={{ height: 48, width: "75%" }} />
          <span style={{ height: 40, width: "90%" }} />
        </div>
      </section>
      <section className="atlas" aria-hidden="true">
        <aside className="theme-spine" />
        <div className="index-panel">
          <div className="skel-bars" style={{ marginTop: 0 }}>
            <span style={{ height: 60 }} />
            <span />
            <span />
            <span />
            <span />
          </div>
        </div>
      </section>
    </>
  );
}

// Riproduce context-bar + workspace (pannello indicatore + mappa/classifica/
// serie storica) al posto del generico LoadingState: DetailView collassa a
// quel blocco non solo al primo mount ma ad ogni cambio indicatore
// (Precedente/Successivo, selezione da classifica), quindi il salto di
// layout altrimenti si ripete durante la navigazione normale.
function DetailViewSkeleton() {
  return (
    <>
      <section className="context-bar" aria-label="Contesto" aria-hidden="true">
        <div className="context-bar__path">
          <span className="skel-bar" style={{ height: 14, width: 220 }} />
        </div>
      </section>
      <section className="workspace" aria-hidden="true">
        <aside className="indicator-panel">
          <div className="skel-bars" style={{ marginTop: 0 }}>
            <span style={{ height: 28 }} />
            <span style={{ height: 60 }} />
            <span style={{ height: 120 }} />
          </div>
        </aside>
        <section className="viz-stage">
          <div className="skel-bars" style={{ marginTop: 0 }}>
            <span style={{ height: 340 }} />
          </div>
        </section>
      </section>
    </>
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
  return `${Math.min(...mins)}-${Math.max(...maxs)}`;
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
  const trendLabel = delta === null ? "n.d." : delta > 0 ? "In crescita" : delta < 0 ? "In calo" : "Stabile";
  const trendText = first && last
    ? `${formatValue(first.value, metadata?.unit)} -> ${formatValue(last.value, metadata?.unit)} (${first.year}-${last.year})`
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
  if (value === null || value === undefined || Number.isNaN(value)) return "n.d.";
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
