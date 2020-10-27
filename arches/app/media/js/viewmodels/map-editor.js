define([
    'arches',
    'jquery',
    'underscore',
    'knockout',
    'knockout-mapping',
    'uuid',
    'mapbox-gl-draw',
    'geojson-extent',
    'geojsonhint',
    'views/components/map',
    'views/components/cards/select-feature-layers',
    'text!templates/views/components/cards/map-popup.htm'
], function(arches, $, _, ko, koMapping, uuid, MapboxDraw, geojsonExtent, geojsonhint, MapComponentViewModel, selectFeatureLayersFactory, popupTemplate){
    var viewModel = function(params) {
        var self = this;
        var padding = 40;
        var drawFeatures;
        var resourceId = params.tile ? params.tile.resourceinstance_id : '';

        this.widgets = params.widgets || [];
        this.newNodeId = null;
        this.featureLookup = {};
        this.selectedFeatureIds = ko.observableArray();
        this.geoJSONString = ko.observable();
        this.draw = null;
        this.selectSource = this.selectSource || ko.observable();
        this.selectSourceLayer = this.selectSourceLayer || ko.observable();

        var selectSource = this.selectSource();
        var selectSourceLayer = this.selectSourceLayer();
        var selectFeatureLayers = selectFeatureLayersFactory(resourceId, selectSource, selectSourceLayer);

        this.setSelectLayersVisibility = function(visibility) {
            var map = self.map();
            if (map) {
                selectFeatureLayers.forEach(function(layer) {
                    map.setLayoutProperty(
                        layer.id,
                        'visibility',
                        visibility ? 'visible' : 'none'
                    );
                });
            }
        };

        var sources = [];
        for (var sourceName in arches.mapSources) {
            if (arches.mapSources.hasOwnProperty(sourceName)) {
                sources.push(sourceName);
            }
        }
        var updateSelectLayers = function() {
            var source = self.selectSource();
            var sourceLayer = self.selectSourceLayer();
            selectFeatureLayers = sources.indexOf(source) > 0 ?
                selectFeatureLayersFactory(resourceId, source, sourceLayer) :
                [];
            self.additionalLayers(
                extendedLayers.concat(
                    selectFeatureLayers,
                    geojsonLayers
                )
            );
        };
        this.selectSource.subscribe(updateSelectLayers);
        this.selectSourceLayer.subscribe(updateSelectLayers);

        this.setDrawTool = function(tool) {
            var showSelectLayers = (tool === 'select_feature');
            self.setSelectLayersVisibility(showSelectLayers);
            if (showSelectLayers) {
                self.draw.changeMode('simple_select');
                self.selectedFeatureIds([]);
            } else {
                if(tool){
                    self.draw.changeMode(tool);
                    self.map().draw_mode = tool;
                }
            }
        };

        self.widgets.forEach(function(widget) {
            var id = ko.unwrap(widget.node_id);
            self.featureLookup[id] = {
                features: ko.computed(function() {
                    var value = koMapping.toJS(self.tile.data[id]);
                    if (value) return value.features;
                    else return [];
                }),
                selectedTool: ko.observable()
            };
            self.featureLookup[id].selectedTool.subscribe(function(tool) {
                if (self.draw) {
                    if (tool === '') {
                        self.draw.trash();
                        self.draw.changeMode('simple_select');
                    } else if (tool) {
                        _.each(self.featureLookup, function(value, key){
                            if (key !== id) {
                                value.selectedTool(null);
                            }
                        });
                        self.newNodeId = id;
                    }
                    self.setDrawTool(tool);
                }
            });
        });

        this.selectedTool = ko.pureComputed(function() {
            var tool;
            _.find(self.featureLookup, function(value){
                var selectedTool = value.selectedTool();
                if(selectedTool) tool = selectedTool;
            });
            return tool;
        });

        this.editing = ko.pureComputed(function(){
            return !!(self.selectedFeatureIds().length > 0 || self.selectedTool());
        });

        this.updateTiles = function() {
            var featureCollection = self.draw.getAll();
            _.each(self.featureLookup, function(value) {
                value.selectedTool(null);
            });
            self.widgets.forEach(function(widget) {
                var id = ko.unwrap(widget.node_id);
                var features = [];
                featureCollection.features.forEach(function(feature){
                    if (feature.properties.nodeId === id) features.push(feature);
                });
                if (ko.isObservable(self.tile.data[id])) {
                    self.tile.data[id]({
                        type: 'FeatureCollection',
                        features: features
                    });
                } else {
                    self.tile.data[id].features(features);
                }
            });
        };

        var getDrawFeatures = function() {
            var drawFeatures = [];
            self.widgets.forEach(function(widget) {
                var id = ko.unwrap(widget.node_id);
                var featureCollection = koMapping.toJS(self.tile.data[id]);
                if (featureCollection) {
                    featureCollection.features.forEach(function(feature) {
                        if (!feature.id) {
                            feature.id = uuid.generate();
                        }
                        feature.properties.nodeId = id;
                    });
                    drawFeatures = drawFeatures.concat(featureCollection.features);
                }
            });
            return drawFeatures;
        };
        drawFeatures = getDrawFeatures();

        if (drawFeatures.length > 0) {
            params.usePosition = false;
            params.bounds = geojsonExtent({
                type: 'FeatureCollection',
                features: drawFeatures
            });
            params.fitBoundsOptions = {padding: { top: padding, left: padding + 200, bottom: padding, right: padding + 200} };
        }
        params.activeTab = 'editor';
        params.sources = Object.assign({
            "geojson-editor-data": {
                "type": "geojson",
                "data": {
                    "type": "FeatureCollection",
                    "features": []
                }
            }
        }, params.sources);
        var extendedLayers = [];
        if (params.layers) {
            extendedLayers = params.layers;
        }

        var geojsonLayers = [{
            /// Fill colour of the polygon once it has been completed
            "id": "geojson-editor-polygon-fill",
            "type": "fill",
            "filter": ["==", "$type", "Polygon"],
            "paint": {
                "fill-color": "#3bb2d0",
                "fill-outline-color": "#3bb2d0",
                "fill-opacity": 0.1
            },
            "source": "geojson-editor-data"
        }, {
            // Base colour for the stroke outline of the polygon
            "id": "geojson-editor-polygon-stroke-base",

            "type": "line",
            "filter": ["==", "$type", "Polygon"],
            "layout": {
                "line-cap": "round",
                "line-join": "round"
            },
            "paint": {
                "line-color": "#fff",
                "line-width": 4
            },
            "source": "geojson-editor-data"
        }, {
            // Main colour for the stroke outline of the polygon
            "id": "geojson-editor-polygon-stroke",
            "type": "line",
            "filter": ["==", "$type", "Polygon"],
            "layout": {
                "line-cap": "round",
                "line-join": "round"
            },
            "paint": {
                "line-color": "#3bb2d0",
                "line-width": 2
            },
            "source": "geojson-editor-data"
        }, {
            // Colour for the polyline
            "id": "geojson-editor-line",
            "type": "line",
            "filter": ["==", "$type", "LineString"],
            "layout": {
                "line-cap": "round",
                "line-join": "round"
            },
            "paint": {
                "line-color": "#3bb2d0",
                "line-width": 2
            },
            "source": "geojson-editor-data"
        }, {
            // Colour for the stroke outline of the point
            "id": "geojson-editor-point-point-stroke",
            "type": "circle",
            "filter": ["==", "$type", "Point"],
            "paint": {
                "circle-radius": 6,
                "circle-opacity": 1,
                "circle-color": "#fff"
            },
            "source": "geojson-editor-data"
        }, {
            "id": "geojson-editor-point",
            "type": "circle",
            "filter": ["==", "$type", "Point"],
            "paint": {
                "circle-radius": 5,
                "circle-color": "#3bb2d0"
            },
            "source": "geojson-editor-data"
        }];

        params.layers = ko.observable(
            extendedLayers.concat(
                selectFeatureLayers,
                geojsonLayers
            )
        );

        MapComponentViewModel.apply(this, [params]);

        this.deleteFeature = function(feature) {
            if (self.draw) {
                self.draw.delete(feature.id);
                self.updateTiles();
            }
        };

        this.editFeature = function(feature) {
            if (self.draw) {
                self.draw.changeMode('simple_select', {
                    featureIds: [feature.id]
                });
                self.selectedFeatureIds([feature.id]);
                _.each(self.featureLookup, function(value) {
                    value.selectedTool(null);
                });
            }
        };

        this.updateLayers = function(layers) {
            var map = self.map();
            var style = map.getStyle();
            if (style) {
                style.layers = self.draw ? layers.concat(self.draw.options.styles) : layers;
                map.setStyle(style);
            }
        };

        this.fitFeatures = function(features) {
            var map = self.map();
            var bounds = geojsonExtent({
                type: 'FeatureCollection',
                features: features
            });
            var camera = map.cameraForBounds(bounds, { padding: padding });
            map.jumpTo(camera);
        };

        this.editGeoJSON = function(features, nodeId) {
            var geoJSONString = JSON.stringify({
                type: 'FeatureCollection',
                features: features
            }, null, '   ');
            this.geoJSONString(geoJSONString);
            self.newNodeId = nodeId;
        };
        this.geoJSONString.subscribe(function(geoJSONString) {
            var map = self.map();
            if (geoJSONString === undefined) {
                setupDraw(map);
            } else if (self.draw) {
                map.removeControl(self.draw);
                self.draw = undefined;
                self.selectedFeatureIds([]);
            }
            self.setSelectLayersVisibility(false);
        });
        this.geoJSONErrors = ko.pureComputed(function() {
            var geoJSONString = self.geoJSONString();
            var hint = geojsonhint.hint(geoJSONString);
            var errors = [];
            hint.forEach(function(item) {
                if (item.level !== 'message') {
                    errors.push(item);
                }
            });
            return errors;
        }).extend({ rateLimit: 50 });
        var geoJSONLayerData = ko.pureComputed(function() {
            var geoJSONString = self.geoJSONString();
            var geoJSONErrors = self.geoJSONErrors();
            if (geoJSONErrors.length === 0) return JSON.parse(geoJSONString);
            else return {
                type: 'FeatureCollection',
                features: []
            };
        }).extend({ rateLimit: 100 });
        geoJSONLayerData.subscribe(function(data) {
            var map = self.map();
            map.getSource('geojson-editor-data').setData(data);
        });
        this.updateGeoJSON = function() {
            if (self.geoJSONErrors().length === 0) {
                var geoJSON = JSON.parse(this.geoJSONString());
                geoJSON.features.forEach(function(feature) {
                    feature.id = uuid.generate();
                    if (!feature.properties) feature.properties = {};
                    feature.properties.nodeId = self.newNodeId;
                });
                if (ko.isObservable(self.tile.data[self.newNodeId])) {
                    self.tile.data[self.newNodeId](geoJSON);
                } else {
                    self.tile.data[self.newNodeId].features(geoJSON.features);
                }
                self.geoJSONString(undefined);
            }
        };
        this.drawStyles = [
            // Set the styles for the drawing point, line and polygon in filter
            // Colour while active should be fill and line: #D60DA3(purple)
            // Colour while inactive should be fill: #E0E0E0(mid-grey) and line: #000000(black)
            // Colour while static should be fill: and line:
            {
                // This sets the colour for the polygon and its outline once
                // the filter has been applied.
                'id': 'gl-draw-polygon-fill-inactive',
                'type': 'fill',
                'filter': ['all',
                    ['==', 'active', 'false'],
                    ['==', '$type', 'Polygon'],
                    ['!=', 'mode', 'static']
                ],
                'paint': {
                    'fill-color': '#D60DA3', //'#3bb2d0',
                    'fill-outline-color': '#000000', //'#3bb2d0',
                    'fill-opacity': 0.5
                }
            },
            {
                // This sets the colour for the polygon and its outline while
                // the filter is being drawn
                'id': 'gl-draw-polygon-fill-active',
                'type': 'fill',
                'filter': ['all',['==', 'active', 'true'],['==', '$type', 'Polygon']],
                'paint': {
                    'fill-color': '#8B40DF', //'#fbb03b',
                    'fill-outline-color': '#8B40DF', //'#fbb03b',
                    'fill-opacity': 0.2
                }
            },
            {
                // This sets the colour of the point at the centre
                // of the polygon
                'id': 'gl-draw-polygon-midpoint',
                'type': 'circle',
                'filter': ['all',
                    ['==', '$type', 'Point'],
                    ['==', 'meta', 'midpoint']],
                'paint': {
                    'circle-radius': 3,
                    'circle-color': '#8B40DF' //'#fbb03b'
                }
            },
            {
                // This sets the properties of the polygon outline
                // once the filter has been applied.
                'id': 'gl-draw-polygon-stroke-inactive',
                'type': 'line',
                'filter': ['all',
                    ['==', 'active', 'false'],
                    ['==', '$type', 'Polygon'],
                    ['!=', 'mode', 'static']
                ],
                'layout': {
                    'line-cap': 'round',
                    'line-join': 'round'
                },
                'paint': {
                    'line-color': '#D60DA3', //'#3bb2d0',
                    'line-width': 2
                }
            },
            {
                // This sets the properties of the polygon outline while
                // the filter is being drawn.
                'id': 'gl-draw-polygon-stroke-active',
                'type': 'line',
                'filter': ['all',['==', 'active', 'true'],['==', '$type', 'Polygon']],
                'layout': {
                    'line-cap': 'round',
                    'line-join': 'round'
                },
                'paint': {
                    'line-color': '#8B40DF', //'#fbb03b',
                    'line-dasharray': [0.2, 2],
                    'line-width': 2
                }
            },
            {
                // This sets the properties of the polyline
                // once the filter has been applied.
                'id': 'gl-draw-line-inactive',
                'type': 'line',
                'filter': ['all',
                    ['==', 'active', 'false'],
                    ['==', '$type', 'LineString'],
                    ['!=', 'mode', 'static']
                ],
                'layout': {
                    'line-cap': 'round',
                    'line-join': 'round'
                },
                'paint': {
                    'line-color': '#D60DA3', //'#3bb2d0',
                    'line-width': 2
                }
            },
            {
                // This sets the properties of the polyline
                // as the filter is being drawn.
                'id': 'gl-draw-line-active',
                'type': 'line',
                'filter': ['all',
                    ['==', '$type', 'LineString'],
                    ['==', 'active', 'true']
                ],
                'layout': {
                    'line-cap': 'round',
                    'line-join': 'round'
                },
                'paint': {
                    'line-color': '#8B40DF', //'#fbb03b',
                    'line-dasharray': [0.2, 2],
                    'line-width': 2
                }
            },
            {
                // This sets the properties of the polygon and polyline vertices outlines
                // once the filter has been drawn.
                'id': 'gl-draw-polygon-and-line-vertex-stroke-inactive',
                'type': 'circle',
                'filter': ['all',
                    ['==', 'meta', 'vertex'],
                    ['==', '$type', 'Point'],
                    ['!=', 'mode', 'static']
                ],
                'paint': {
                    'circle-radius': 5,
                    'circle-color': '#fff'
                }
            },
            {
                // This sets the properties of the polygon and polyline vertices
                // once the filter has been drawn.
                'id': 'gl-draw-polygon-and-line-vertex-inactive',
                'type': 'circle',
                'filter': ['all',
                    ['==', 'meta', 'vertex'],
                    ['==', '$type', 'Point'],
                    ['!=', 'mode', 'static']
                ],
                'paint': {
                    'circle-radius': 3,
                    'circle-color': '#8B40DF' //'#fbb03b'
                }
            },
            {
                // This sets the properties of the point outline
                // once the filter has been drawn.
                'id': 'gl-draw-point-point-stroke-inactive',
                'type': 'circle',
                'filter': ['all',
                    ['==', 'active', 'false'],
                    ['==', '$type', 'Point'],
                    ['==', 'meta', 'feature'],
                    ['!=', 'mode', 'static']
                ],
                'paint': {
                    'circle-radius': 5,
                    'circle-opacity': 1,
                    'circle-color': '#fff'
                }
            },
            {
                // This sets the properties of the point
                // once the filter has been drawn.
                'id': 'gl-draw-point-inactive',
                'type': 'circle',
                'filter': ['all',
                    ['==', 'active', 'false'],
                    ['==', '$type', 'Point'],
                    ['==', 'meta', 'feature'],
                    ['!=', 'mode', 'static']
                ],
                'paint': {
                    'circle-radius': 3,
                    'circle-color': '#D60DA3'
                }
            },
            {
                // This sets the properties of the point outline
                // while the filter is being drawn.
                'id': 'gl-draw-point-stroke-active',
                'type': 'circle',
                'filter': ['all',
                    ['==', '$type', 'Point'],
                    ['==', 'active', 'true'],
                    ['!=', 'meta', 'midpoint']
                ],
                'paint': {
                    'circle-radius': 7,
                    'circle-color': '#fff'
                }
            },
            {
                // This sets the properties of the point
                // while the filter is being drawn.
                'id': 'gl-draw-point-active',
                'type': 'circle',
                'filter': ['all',
                    ['==', '$type', 'Point'],
                    ['!=', 'meta', 'midpoint'],
                    ['==', 'active', 'true']],
                'paint': {
                    'circle-radius': 5,
                    'circle-color': '#8B40DF' //'#fbb03b'
                }
            },
            {
                // This sets the colour for the polygon and its outline once
                // the draw mode has been changed to 'static'
                'id': 'gl-draw-polygon-fill-static',
                'type': 'fill',
                'filter': ['all',['==', 'mode', 'static'],['==', '$type', 'Polygon']],
                'paint': {
                    'fill-color': '#D60DA3',
                    'fill-outline-color': '#D60DA3',
                    'fill-opacity': 0.1
                }
            },
            {
                // This sets the properties of the polygon outline once
                // the draw mode has been changed to 'static'
                'id': 'gl-draw-polygon-stroke-static',
                'type': 'line',
                'filter': ['all',['==', 'mode', 'static'],['==', '$type', 'Polygon']],
                'layout': {
                    'line-cap': 'round',
                    'line-join': 'round'
                },
                'paint': {
                    'line-color': '#D60DA3',
                    'line-width': 2
                }
            },
            {
                // This sets the properties of the polyline once
                // the draw mode has been changed to 'static'
                'id': 'gl-draw-line-static',
                'type': 'line',
                'filter': ['all',['==', 'mode', 'static'],['==', '$type', 'LineString']],
                'layout': {
                    'line-cap': 'round',
                    'line-join': 'round'
                },
                'paint': {
                    'line-color': '#D60DA3',
                    'line-width': 2
                }
            },
            {
                // This sets the properties of the point once
                // the draw mode has been changed to 'static'
                'id': 'gl-draw-point-static',
                'type': 'circle',
                'filter': ['all',['==', 'mode', 'static'],['==', '$type', 'Point']],
                'paint': {
                    'circle-radius': 5,
                    'circle-color': '#D60DA3'
                }
            }
        ];

        var setupDraw = function(map) {
            var modes = MapboxDraw.modes;
            modes.static = {
                onSetup: function() {
                    this.setActionableState();
                    return {};
                },
                toDisplayFeatures: function(state, geojson, display) {
                    display(geojson);
                }
            };
            self.draw = new MapboxDraw({
                displayControlsDefault: false,
                modes: modes,
                styles: self.drawStyles
            });
            map.addControl(self.draw);
            self.draw.set({
                type: 'FeatureCollection',
                features: getDrawFeatures()
            });
            map.on('draw.create', function(e) {
                e.features.forEach(function(feature) {
                    self.draw.setFeatureProperty(feature.id, 'nodeId', self.newNodeId);
                });
                self.updateTiles();
            });
            map.on('draw.update', self.updateTiles);
            map.on('draw.delete', self.updateTiles);
            map.on('draw.modechange', function(e) {
                self.updateTiles();
                self.setSelectLayersVisibility(false);
                map.draw_mode = e.mode;
            });
            map.on('draw.selectionchange', function(e) {
                self.selectedFeatureIds(e.features.map(function(feature) {
                    return feature.id;
                }));
                if (e.features.length > 0) {
                    _.each(self.featureLookup, function(value) {
                        value.selectedTool(null);
                    });
                }
                self.setSelectLayersVisibility(false);
            });

            if (self.form) self.form.on('tile-reset', function() {
                var style = self.map().getStyle();
                if (style) {
                    self.draw.set({
                        type: 'FeatureCollection',
                        features: getDrawFeatures()
                    });
                }
                _.each(self.featureLookup, function(value) {
                    if (value.selectedTool()) value.selectedTool('');
                });
            });
        };


        if (this.provisionalTileViewModel) {
            this.provisionalTileViewModel.resetAuthoritative();
            this.provisionalTileViewModel.selectedProvisionalEdit.subscribe(function(val){
                if (val) {
                    var displayAll = function(){
                        var featureCollection;
                        for (var k in self.tile.data){
                            if (self.featureLookup[k] && self.draw) {
                                try {
                                    featureCollection = self.draw.getAll();
                                    featureCollection.features = ko.unwrap(self.featureLookup[k].features);
                                    self.draw.set(featureCollection);
                                } catch(e) {
                                    //pass: TypeError in draw seems inconsequential.
                                }
                            }
                        }
                    };
                    setTimeout(displayAll, 100);
                }
            });
        }

        this.map.subscribe(setupDraw);

        if (!params.additionalDrawOptions) {
            params.additionalDrawOptions = [];
        }

        self.widgets.forEach(function(widget) {
            if (widget.config.geometryTypes) {
                widget.drawTools = ko.pureComputed(function() {
                    var options = [{
                        value: '',
                        text: ''
                    }];
                    options = options.concat(
                        ko.unwrap(widget.config.geometryTypes).map(function(type) {
                            var option = {};
                            switch (ko.unwrap(type.id)) {
                                case 'Point':
                                    option.value = 'draw_point';
                                    option.text = 'Add point';
                                    break;
                                case 'Line':
                                    option.value = 'draw_line_string';
                                    option.text = 'Add line';
                                    break;
                                case 'Polygon':
                                    option.value = 'draw_polygon';
                                    option.text = 'Add polygon';
                                    break;
                            }
                            return option;
                        })
                    );
                    if (self.selectSource()) {
                        options.push({
                            value: "select_feature",
                            text: self.selectText() || 'Select drawing'
                        });
                    }
                    options = options.concat(params.additionalDrawOptions);
                    return options;
                });
            }
        });

        this.isFeatureClickable = function(feature) {
            var tool = self.selectedTool();
            if (tool && tool !== 'select_feature') return false;
            return feature.properties.resourceinstanceid;
        };

        this.popupTemplate = popupTemplate;

        self.isSelectable = function(feature) {
            var selectLayerIds = selectFeatureLayers.map(function(layer) {
                return layer.id;
            });
            return selectLayerIds.indexOf(feature.layer.id) >= 0;
        };

        var addSelectFeatures = function(features) {
            var featureIds = [];
            features.forEach(function(feature) {
                feature.id = uuid.generate();
                feature.properties = {
                    nodeId: self.newNodeId
                };
                self.draw.add(feature);
                featureIds.push(feature.id);
            });
            self.updateTiles();
            self.popup.remove();
            self.draw.changeMode('simple_select', {
                featureIds: featureIds
            });
            self.selectedFeatureIds(featureIds);
            _.each(self.featureLookup, function(value) {
                value.selectedTool(null);
            });
        };

        self.selectFeature = function(feature) {
            try{
                var geometry = JSON.parse(feature.properties.geojson);
                var newFeature = {
                    "type": "Feature",
                    "properties": {},
                    "geometry": geometry
                };
                addSelectFeatures([newFeature]);
            } catch(e){
                $.getJSON(feature.properties.geojson, function(data) {
                    addSelectFeatures(data.features);
                });
            }
        };
    };
    return viewModel;
});
