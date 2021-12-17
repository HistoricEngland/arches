----------- datatype label functions

--drop function if exists get_concept_label;
create or replace function get_concept_label(concept_value text) returns text language plpgsql as $$
declare
	concept_label text := '';
begin
	select v.value
	into concept_label
	from values v
	where v.valueid = concept_value::uuid;

	if concept_label is null then
		concept_label := '';
	end if;
	
return concept_label;
end;
$$;

--drop function if exists get_concept_list_label;
create or replace function get_concept_list_label(concept_array jsonb) returns text language plpgsql as $$
declare
	concept_list text;
begin

	select string_agg(d.label, ', ')
	from
	(
		select get_concept_label(x.conceptid) as label
		from (select json_array_elements_text(concept_array::json) as conceptid) x
	 ) d
	into concept_list;
	
	if (concept_list is null) then
		concept_list := '';
	end if;
 
return concept_list;
end;
$$;

--drop function if exists get_domain_label;
create or replace function get_domain_label(domain_value text, in_nodeid text) returns text language plpgsql as $$
declare
	in_node_config jsonb;
	return_label text;
begin
 	if domain_value is null or domain_value = '' or in_nodeid = '' then
		return '';
	end if;	
	
	-- get the node config to access domaint options
	select n.config
	into in_node_config
	from nodes n
	where n.nodeid = in_nodeid::uuid;
		
	-- get the domain options text from the config
	select opt.text
		into return_label
	from jsonb_populate_recordset(in_node_config -> 'options') opts
	where opts.text = domain_value;
	
	if return_label is null then
		return_label = '';
	end if;
	
return return_label;
end;
$$;

--drop function if exists get_domain_list_label;
create or replace function get_domain_list_label(domain_value_list jsonb, nodeid text) returns text language plpgsql as $$
declare
	return_label text := '';
begin
 	if domain_value_list is null or in_nodeid = '' then
		return '';
	end if;
	
	select string_agg(dvl.label, ', ')
	from
	(
		select get_domain_label(dv.domain_value) as label
		from (
			select jsonb_array_elements_text(domain_value_list::json) as domain_value
		) dv
	 ) dvl
	into return_label;
	
return return_label;
end;
$$;


--drop function if exists get_resourceinstance_label;
create or replace function get_resourceinstance_label(resourceinstance_value jsonb, label_type text default 'name') returns text language plpgsql as $$
declare
	return_label text := '';
	--return_label text := '<resource-instance>';
	
	target_resourceinstanceid uuid;
	target_graph_funct_config jsonb;
	target_graphid uuid;
	target_nodegroupid uuid;
	target_template text;
	target_tiledata jsonb;
	target_provisionaledits jsonb;
	target_data jsonb;
begin

 	if resourceinstance_value is null or resourceinstance_value::text = 'null' then
		raise notice 'resourceinstance_value is null';
		return return_label;
	end if;
	
	
	target_resourceinstanceid := ((resourceinstance_value -> 0) ->> 'resourceId')::uuid;
	if target_resourceinstanceid is null then
		target_resourceinstanceid := (resourceinstance_value ->> 'resourceId')::uuid;
	end if;
	if target_resourceinstanceid is null then
		raise notice 'target_resourceinstanceid: % ## resourceinstance_value: %)', target_resourceinstanceid, resourceinstance_value;	
		return return_label;
	end if;
	
	select r.graphid
	into target_graphid
	from resource_instances r
	where resourceinstanceid = target_resourceinstanceid;
	
	select fxg.config
	into target_graph_funct_config
	from functions_x_graphs fxg
	join functions f on fxg.functionid = f.functionid
	where f.functiontype = 'primarydescriptors'
		AND fxg.graphid = target_graphid;
	
	if target_graph_funct_config is null then
		raise notice 'target_graph_funct_config is null for graphid (%)', target_graphid;
		return return_label;
	end if;
	

	if jsonb_path_exists(target_graph_funct_config, format('$.%s.nodegroup_id',label_type)::jsonpath) then
		target_nodegroupid := (target_graph_funct_config::json #>> format('{%s,nodegroup_id}',label_type)::text[])::uuid;
		if target_nodegroupid::text = '' then
			raise notice 'target_nodegroupid is an empty string';
			return return_label;
		end if;					
	end if;
	
	if jsonb_path_exists(target_graph_funct_config, format('$.%s.string_template',label_type)::jsonpath) then
		target_template := (target_graph_funct_config::json #>> format('{%s,string_template}',label_type)::text[])::text;
		if target_template::text = '' then
			raise notice 'target_template is an empty string';
			return return_label;
		end if;					
	end if;
	
	select t.tiledata, t.provisionaledits
	into target_tiledata, target_provisionaledits
	from tiles t
	where t.nodegroupid = target_nodegroupid
		and t.resourceinstanceid = target_resourceinstanceid
	order by t.sortorder nulls last
	limit 1;

	if target_tiledata is null and target_provisionaledits is null then
		return return_label;
	end if;

	-- decide if to use the tiledata or the provisionaledits
	/*
                    for node in models.Node.objects.filter(nodegroup_id=uuid.UUID(config["nodegroup_id"])):
                        data = {}
                        if len(list(tile.data.keys())) > 0:
                            data = tile.data
                        elif tile.provisionaledits is not None and len(list(tile.provisionaledits.keys())) == 1:
                            userid = list(tile.provisionaledits.keys())[0]
                            data = tile.provisionaledits[userid]["value"]
	*/
	target_data := '{}'::jsonb;
	
	declare
		tiledata_keycount integer := 0;
		provisionaledits_users_keycount integer := 0;
		provisionaledits_userid text;
	begin
		select count(*) from jsonb_object_keys(target_tiledata) into tiledata_keycount;
		if tiledata_keycount > 0 then
			target_data := target_tiledata;
		else
			if target_provisionaledits is not null then
				select count(*) from jsonb_object_keys(target_provisionaledits) into provisionaledits_users_keycount;
				if provisionaledits_users_keycount == 1 then
					select u.userid::text from (select userid FROM json_each_text(data) LIMIT 1) u into provisionaledits_userid;
					target_data := (target_provisionaledits ->> userid)::jsonb;
				end if;
			end if;
		end if;
	end;	
	
	--target_data := target_tiledata;
	
	declare
		n record;
	begin
		for n in select *
			from nodes
			where nodegroupid = target_nodegroupid
		loop
			if target_template like format('%%<%s>%%',n.name) then
				select replace(target_template, format('<%s>',n.name), get_node_display_value(target_data, n.nodeid::text)) into target_template;
			end if;
		end loop;	
	end;
	
	return_label := trim(both from target_template);
	if return_label = '' then
		return 'Undefined';
	end if;
	return return_label;
end;
$$;

--drop function if exists get_resourceinstance_list_label;
create or replace function get_resourceinstance_list_label(resourceinstance_value jsonb, label_type text default 'name') returns text language plpgsql as $$
declare
	return_label text := '';
begin
 	if resourceinstance_value is null then
		return '';
	end if;
	
	select string_agg(dvl.label, ', ')
	from
	(
		select get_resourceinstance_label(dv.resource_instance, label_type) as label
		from (
			select jsonb_array_elements_text(resourceinstance_value) as resource_instance
		) dv
	 ) dvl
	into return_label;
	
return return_label;
end;
$$;


--drop function if exists get_nodevalue_label;
create or replace function get_nodevalue_label(node_value jsonb, in_nodeid text) returns text language plpgsql as $$
declare
	return_label text := '';
	nodevalue_tileid text;
	value_nodeid text;
begin

	if node_value is null or in_nodeid is null or in_nodeid = '' then
		return '';
	end if;
	
	-- get the target node id
	select n.config ->> 'nodeid'
	into value_nodeid
	from nodes n
	where n.nodeid = in_nodeid::uuid;

	
	-- get the display value for the target nodeid in the target tile
	select get_node_display_value(t.tiledata, value_nodeid)
	into return_label
	from tiles t
	where t.tileid = node_value::uuid; --node_value will be the tileid for where the data
	
	if return_label is null then
		return_label := '';
	end if;
	
return return_label;
end;
$$;

--######################################## display value ###################################################--

--drop function if exists get_node_display_value;
create or replace function get_node_display_value(in_tiledata jsonb, in_nodeid text) returns text language plpgsql as $$
declare
	display_value text := '';
	in_node_type text;
	in_node_config json;
begin
	if in_nodeid is null or in_nodeid = '' then
		return '<invalid_nodeid>';
	end if;
	
	if in_tiledata is null then
		return '';
	end if;
	
	-- get node type
 	select n.datatype, n.config 
	into in_node_type, in_node_config 
	from nodes n where nodeid = in_nodeid::uuid;
		
	if in_node_type = 'semantic' then
		return '<semantic>';
	end if;
	
	if in_node_type is null then
		return '';
	end if;
	
	-- broadly translated from the python datatype classes
	case in_node_type
		when 'concept' then
			display_value := get_concept_label(in_tiledata ->> in_nodeid);
		when 'concept-list' then
			display_value := get_concept_list_label(in_tiledata -> in_nodeid);
		when 'edtf' then
			display_value := ((in_tiledata -> in_nodeid) ->> 'value');
		when 'file-list' then
			select string_agg(f.url,' | ') from (select (jsonb_array_elements(in_tiledata -> in_nodeid) -> 'name')::text as url) f into display_value;
		when 'domain-value' then
			display_value := get_domain_label(in_tiledata -> in_nodeid, in_nodeid);
		when 'domain-value-list' then
			display_value := get_domain_list_label(in_tiledata -> in_nodeid, in_nodeid);
		when 'url' then
			display_value := (in_tiledata -> in_nodeid ->> 'url');
		when 'node-value' then
			display_value := get_nodevalue_label(in_tiledata -> in_nodeid, in_nodeid);
		when 'resource-instance' then
			display_value := get_resourceinstance_label(in_tiledata -> in_nodeid, 'name');
		when 'resource-instance-list' then
			display_value := get_resourceinstance_list_label(in_tiledata -> in_nodeid, 'name');
		else
			-- print the content of the json
			-- 'string'
			-- 'number'
			-- 'date' -----------------might need to look at date formatting?
			-- 'bngcentrepoint'
			-- 'boolean
			-- 'geojson-feature-collection'
			-- 'annotation'
			display_value := (in_tiledata ->> in_nodeid)::text;
		
		end case;
			
	return display_value;
end;
$$;

--###################################### aggregation functions ############################################--

--drop function if exists accum_get_node_display_value;
create or replace function accum_get_node_display_value(init text, in_tiledata jsonb, in_nodeid text) returns text language plpgsql as $$
declare
	display_name text := '';
	return_label text := '';
begin

	select
		get_node_display_value(in_tiledata, in_nodeid)
	into display_name;
	
	if display_name = '' then
		return init;
	end if;
	
	if init = '' then
		return_label := display_name;
	else
		return_label := (init || ', ' || display_name);
	end if;
	
	return return_label;
end;
$$;

--drop function if exists agg_get_node_display_value;
create or replace aggregate agg_get_node_display_value(in_tiledata jsonb, in_nodeid text)
(
	initcond = '',
	stype = text,
	sfunc = accum_get_node_display_value
);

/* EXAMPLE FOR KEYSTONE
-------------------------------------------------------------------
-- heritage asset geospatial_coords nodeid
-- drop materialized view if exists public.attribute_87d3d7dc_f44f_11eb_bee9_a87eeabdefba;

-- create materialized view attribute_87d3d7dc_f44f_11eb_bee9_a87eeabdefba 
--tablespace pg_default
--as
--(
	select 
		r.resourceinstanceid
		-------------- nodes -----------
		,agg_get_node_display_value(distinct t_1.tiledata, '325a2f33-efe4-11eb-b0bb-a87eeabdefba')as primary_reference_number

		-- 676d47f9-9c1c-11ea-9aa0-f875a44e0e11 - assetname
		,agg_get_node_display_value(distinct t_2.tiledata, '676d47ff-9c1c-11ea-b07f-f875a44e0e11') as asset_name

		-- ba345577-b554-11ea-a9ee-f875a44e0e11 - assetdescription
		,agg_get_node_display_value(distinct t_3.tiledata, 'ba345577-b554-11ea-a9ee-f875a44e0e11') as asset_description

		-- 77e8f29d-efdc-11eb-b890-a87eeabdefba - culturalperiod (resourceinstance type)
		,agg_get_node_display_value(distinct t_4.tiledata, '77e8f29d-efdc-11eb-b890-a87eeabdefba') as cultural_period

		-- 77e8f28d-efdc-11eb-afe4-a87eeabdefba - constructionphasetype (concept type)
		,agg_get_node_display_value(distinct t_4.tiledata, '77e8f28d-efdc-11eb-afe4-a87eeabdefba') as construction_phase_type

		-- b2133e72-efdc-11eb-a68d-a87eeabdefba - usephaseperiod (resourceinstance type)
		,agg_get_node_display_value(distinct t_5.tiledata, 'b2133e72-efdc-11eb-a68d-a87eeabdefba') as use_phase_period

		-- b2133e6b-efdc-11eb-aa04-a87eeabdefba - functionaltype (concept-list)
		,agg_get_node_display_value(distinct t_5.tiledata, 'b2133e6b-efdc-11eb-aa04-a87eeabdefba') as functional_type
		--------------------------------

	from resource_instances r
		------------filter to those with geometries-----------------------

		join geojson_geometries geo on geo.resourceinstanceid = r.resourceinstanceid
			and geo.nodeid = '87d3d7dc-f44f-11eb-bee9-a87eeabdefba'

		------------node tiles-------------
		left outer join tiles t_1 on r.resourceinstanceid = t_1.resourceinstanceid
			and t_1.nodegroupid = '325a2f2f-efe4-11eb-9b0c-a87eeabdefba'
		
		left outer join tiles t_2 on r.resourceinstanceid = t_2.resourceinstanceid
			and t_2.nodegroupid = '676d47f9-9c1c-11ea-9aa0-f875a44e0e11'

		left outer join tiles t_3 on r.resourceinstanceid = t_3.resourceinstanceid
			and t_3.nodegroupid = 'ba342e69-b554-11ea-a027-f875a44e0e11'

		left outer join tiles t_4 on r.resourceinstanceid = t_4.resourceinstanceid
			and t_4.nodegroupid = '77e8f287-efdc-11eb-a790-a87eeabdefba'
		
		left outer join tiles t_5 on r.resourceinstanceid = t_5.resourceinstanceid
			and t_5.nodegroupid = 'b2133dda-efdc-11eb-ab07-a87eeabdefba'

	group by
		r.resourceinstanceid
	limit 1000
	;

--)
--with data;
*/