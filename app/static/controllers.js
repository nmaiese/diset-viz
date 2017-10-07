function get_value_by_theme(data, tema){
    return data.filter(function(d){ return d.Tema == tema });
}

function get_value_by_indicator(data, indicatore){
    return data.filter(function(d){ return d.Indicatore == indicatore });
}

function get_value_by_year(data, anno){
    return data.filter(function(d){ return d.Anno == anno });
}

function get_value_by_region(data, regione){
    return data.filter(function(d){ return d.Regione == regione });
}

function get_data_subset(data, params){
    return data.filter(function(d){return d.Indicatore == parms.indicatore && d.Tema == params.tema });
}

function get_data_for_chart(data, params, indicatore, update_chart){
    var data_by_region = get_value_by_region(data, params.anno);
    var data_by_year = get_value_by_year(data, params.regione);
    return {'region': data_by_region, 'year': data_by_year };
}

function update_charts(c_data, c_map=false, c_region=false, c_year=false){
    (c_map) ? c_map.features(c_data.data_by_region).update();
    (c_region) ? c_region.data(c_data.data_by_region).update();
    (c_year) ? c_year.features(c_data.data_by_year).update();
}


function get_dataset_and_map_geo(data, geodata, indicatore, anno){
    data = data.filter(function(d){return (d.Indicatore == indicatore && d.Anno == anno)})
    geodata.forEach(function(d) {
        data = replace_missing_value(data, d.properties.name)
        v = data.filter(function(f) { return d.properties.name == f.Regione })
        d.dati = v[0]
    })
    return geodata
}

