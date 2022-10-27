define([
    'knockout',
    'views/components/workflows/new-tile-step',
    'viewmodels/alert'
], function(ko, NewTileStepViewModel, AlertViewModel) {

    /** 
     * A generic viewmodel for workflow steps that can add multiple tiles
     * @name NewMultiTileStepViewModel
     **/

    function NewMultiTileStepViewModel(params) {
        NewTileStepViewModel.apply(this, [params]);
        var self = this;
        this.itemName = ko.observable();
        params.title() != undefined ? this.itemName(params.title()) : this.itemName('Items');

        this.remove = function(tile) {
            params.pageVm.alert(            
                new AlertViewModel(
                    'ep-alert-red',
                    'Item Deletion.',
                    'Are you sure you would like to delete this item?',
                    function(){}, //does nothing when canceled
                    function(tile) {
                        tile.deleteTile( function(response) {
                            self.alert(new AlertViewModel(
                                'ep-alert-red', 
                                response.responseJSON.title,
                                response.responseJSON.message,
                                null, 
                                function(){ return; }
                            ));
                        });
                    })
            );
        };

        this.edit = function(tile) { self.tile(tile); };

        self.onSaveSuccess = function(tile) {
            params.resourceid(tile.resourceinstance_id);
            params.tileid(tile.tileid);
            self.resourceId(tile.resourceinstance_id);
            self.tile(self.card().getNewTile());
            self.tile().reset();
            setTimeout(function() {
                self.tile().reset();
            }, 1);
        };

        var updateTileOnInit = self.tile.subscribe(function() {
            updateTileOnInit.dispose();
            self.tile(self.card().getNewTile());
        });
    }
    ko.components.register('new-multi-tile-step', {
        viewModel: NewMultiTileStepViewModel,
        template: {
            require: 'text!templates/views/components/workflows/new-multi-tile-step.htm'
        }
    });
    return NewMultiTileStepViewModel;
});
