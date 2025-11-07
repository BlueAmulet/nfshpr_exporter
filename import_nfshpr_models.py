#-*- coding:utf-8 -*-

# Blender Need for Speed Hot Pursuit (2010/2020) importer Add-on
# Add-on developed by DGIorio with contributions and tests by Piotrek


## TO DO
"""
- Import Beta X360 files
"""

bl_info = {
	"name": "Import Need for Speed Hot Pursuit (2010/2020) models format (.BIN, .BNDL, .dat)",
	"description": "Import meshes files from Need for Speed Hot Pursuit (2010/2020) PC",
	"author": "DGIorio",
	"version": (1, 2, 1),
	"blender": (3, 1, 0),
	"location": "File > Import > Need for Speed Hot Pursuit (2010/2020) (.dat)",
	"warning": "",
	"wiki_url": "",
	"tracker_url": "",
	"support": "COMMUNITY",
	"category": "Import-Export"}


import bpy
from bpy.types import Operator
from bpy.props import (
	StringProperty,
	BoolProperty,
	EnumProperty
)
from bpy_extras.io_utils import (
	ImportHelper,
	orientation_helper,
	axis_conversion,
)
import bmesh
import binascii
import math
from mathutils import Matrix, Vector, Quaternion, Euler
import os
import time
import shutil
import struct
from numpy import frombuffer
from bundle_packer_unpacker import unpack_bundle_hp
import tempfile
import zlib
import random
from io import BytesIO
try:
	from import_nfshpr_ps3_models import main_ps3
except:
	pass


def main(context, file_path, resource_version, resource_type, is_bundle, clear_scene, debug_prefer_shared_asset, hide_low_lods, hide_polygonsoup, hide_skeleton, hide_controlmesh, hide_effects, random_color, global_matrix):
	os.system('cls')

	if bpy.ops.object.mode_set.poll():
		bpy.ops.object.mode_set(mode='OBJECT')

	if clear_scene == True:
		print("Clearing scene...")
		clearScene(context)

	if resource_version == "NFSHPR_PC":
		status = main_pc(context, file_path, resource_version, resource_type, is_bundle, clear_scene, hide_low_lods, hide_polygonsoup, hide_skeleton, hide_controlmesh, hide_effects, random_color, global_matrix)
	elif resource_version == "NFSHP_PC":
		status = main_pc(context, file_path, resource_version, resource_type, is_bundle, clear_scene, hide_low_lods, hide_polygonsoup, hide_skeleton, hide_controlmesh, hide_effects, random_color, global_matrix)
	elif resource_version == "NFSHP_PS3":
		try:
			with Suppressor():
				status = main_ps3(context, file_path, resource_version, resource_type, is_bundle, clear_scene, hide_low_lods, hide_polygonsoup, hide_skeleton, hide_controlmesh, hide_effects, random_color, global_matrix)
		except:
			print("ERROR: file version not supported yet.")
			status = {'CANCELLED'}
	elif resource_version == "NFSHP_X360":
		print("ERROR: file version not supported yet.")
		status = {'CANCELLED'}
	else:
		print("ERROR: file version not supported yet.")
		status = {'CANCELLED'}

	return status


def main_pc(context, file_path, resource_version, resource_type, is_bundle, clear_scene, hide_low_lods, hide_polygonsoup, hide_skeleton, hide_controlmesh, hide_effects, random_color, m):
	## INITIALIZING
	start_time = time.time()

	print("Importing file %s" % os.path.basename(file_path))
	print("Initializing variables...")
	if is_bundle == True:
		temp_dir = tempfile.TemporaryDirectory()
		directory_path = temp_dir.name
	else:
		directory_path = os.path.dirname(os.path.dirname(file_path))
	instancelist_dir = os.path.join(directory_path, "InstanceList")
	polygonsouplist_dir = os.path.join(directory_path, "PolygonSoupList")
	controlmesh_dir = os.path.join(directory_path, "ControlMesh")
	skeleton_dir = os.path.join(directory_path, "Skeleton")
	lightinstancelist_dir = os.path.join(directory_path, "LightInstanceList")
	dynamicinstancelist_dir = os.path.join(directory_path, "DynamicInstanceList")
	zoneheader_dir = os.path.join(directory_path, "ZoneHeader")
	worldobject_dir = os.path.join(directory_path, "WorldObject")

	genesyinstance_dir = os.path.join(directory_path, "GenesysInstance")

	characterspec_dir = os.path.join(directory_path, "CharacterSpec")
	graphicsspec_dir = os.path.join(directory_path, "GraphicsSpec")
	model_dir = os.path.join(directory_path, "Model")
	renderable_dir = os.path.join(directory_path, "Renderable")
	vertex_descriptor_dir = os.path.join(directory_path, "VertexDescriptor")
	material_dir = os.path.join(directory_path, "Material")
	raster_dir = os.path.join(directory_path, "Texture")

	triggerdata_dir = os.path.join(directory_path, "TriggerData")

	zonelist_dir = os.path.join(directory_path, "ZoneList")

	if resource_version == "NFSHPR_PC":
		shared_dir = os.path.join(NFSHPLibraryGet(), "NFSHPR_Library_PC")
	elif resource_version == "NFSHP_PC":
		shared_dir = os.path.join(NFSHPLibraryGet(), "NFSHP_Library_PC")
	elif resource_version == "NFSHP_PS3":
		shared_dir = os.path.join(NFSHPLibraryGet(), "NFSHP_Library_PS3")
	elif resource_version == "NFSHP_X360":
		shared_dir = os.path.join(NFSHPLibraryGet(), "NFSHP_Library_X360")
	else:
		shared_dir = os.path.join(NFSHPLibraryGet(), "NFSHP_Library_PC")
	shared_worldobject_dir = os.path.join(shared_dir, "WorldObject")
	shared_model_dir = os.path.join(shared_dir, "Model")
	shared_renderable_dir = os.path.join(shared_dir, "Renderable")
	shared_vertex_descriptor_dir = os.path.join(os.path.join(shared_dir, "SHADERS"), "VertexDescriptor")
	shared_material_dir = os.path.join(shared_dir, "Material")
	shared_shader_dir = os.path.join(os.path.join(shared_dir, "SHADERS"), "Shader")
	shared_raster_dir = os.path.join(shared_dir, "Texture")
	characterLibrary = os.path.join(shared_dir, "CHARACTERS", "ALL_CHARS.blend")

	track_unit_number = None

	instances = []
	instance_character = []
	instances_wheel = []
	instances_effects = []
	instances_dynamic = []
	lights = []
	models = {}
	renderables = []
	vertex_descriptors = []
	materials = []
	shaders = []
	rasters = []
	PolygonSoups = []
	Skeleton = []
	ControlMeshes = []
	triggers = []

	renderable_objects = []

	#m = axis_conversion(from_forward='-Y', from_up='Z', to_forward='-Z', to_up='X').to_4x4()
	#m = axis_conversion(from_forward='Z', from_up='Y', to_forward='-Y', to_up='Z').to_4x4()

	if is_bundle == True:
		main_collection_name = os.path.basename(file_path).split(".")[0]
	else:
		if resource_type == "GraphicsSpec":
			main_collection_name = "VEH_" + str(id_to_int(os.path.basename(file_path).split(".")[0][0:11]))
		elif resource_type == "CharacterSpec":
			main_collection_name = "CHR_" + str(id_to_int(os.path.basename(file_path).split(".")[0][0:11]))
		else:
			main_collection_name = os.path.basename(file_path).split(".")[0]


	## UNPACKING FILE
	if is_bundle == True:
		print("Unpacking file...")
		unpacking_time = time.time()

		status = unpack_bundle_hp(file_path, directory_path, "hpr", "IDs_" + os.path.basename(file_path))

		elapsed_time = time.time() - unpacking_time

		if status == 1:
			return {'CANCELLED'}
		print("... %.4fs" % elapsed_time)

		if resource_type == "InstanceList":
			if not os.path.isdir(instancelist_dir):
				print("ERROR: non-existent path %s. Verify if you selected the correct resource type to import and try again. You had selected to import the file as %s." % (instancelist_dir, resource_type))
				return {'CANCELLED'}
			file_path = os.path.join(instancelist_dir, os.listdir(instancelist_dir)[0])

		elif resource_type == "GraphicsSpec":
			if not os.path.isdir(graphicsspec_dir):
				print("ERROR: non-existent path %s. Verify if you selected the correct resource type to import and try again. You had selected to import the file as %s." % (graphicsspec_dir, resource_type))
				return {'CANCELLED'}
			file_path = os.path.join(graphicsspec_dir, os.listdir(graphicsspec_dir)[0])

		elif resource_type == "CharacterSpec":
			if not os.path.isdir(characterspec_dir):
				print("ERROR: non-existent path %s. Verify if you selected the correct resource type to import and try again. You had selected to import the file as %s." % (characterspec_dir, resource_type))
				return {'CANCELLED'}
			file_path = os.path.join(characterspec_dir, os.listdir(characterspec_dir)[0])

		elif resource_type == "TriggerData":
			if not os.path.isdir(triggerdata_dir):
				print("ERROR: non-existent path %s. Verify if you selected the correct resource type to import and try again. You had selected to import the file as %s." % (triggerdata_dir, resource_type))
				return {'CANCELLED'}
			file_path = os.path.join(triggerdata_dir, os.listdir(triggerdata_dir)[0])

		elif resource_type == "ZoneList":
			if not os.path.isdir(zonelist_dir):
				print("ERROR: non-existent path %s. Verify if you selected the correct resource type to import and try again. You had selected to import the file as %s." % (zonelist_dir, resource_type))
				return {'CANCELLED'}
			file_path = os.path.join(zonelist_dir, os.listdir(zonelist_dir)[0])

		elif resource_type == "PolygonSoupList":
			if not os.path.isdir(polygonsouplist_dir):
				print("ERROR: non-existent path %s. Verify if you selected the correct resource type to import and try again. You had selected to import the file as %s." % (polygonsouplist_dir, resource_type))
				return {'CANCELLED'}
			file_path = os.path.join(polygonsouplist_dir, os.listdir(polygonsouplist_dir)[0])

	## PARSING FILES
	print("Parsing files...")
	parsing_time = time.time()

	mMainId = os.path.splitext(os.path.basename(file_path))[0][:11]
	if resource_type == "InstanceList":
		track_unit_number = decode_resource_id(mMainId, resource_type)
		track_unit_number = int(track_unit_number.replace("TRK_UNIT", ""))

		instances = read_instancelist(file_path, resource_version)

		mInstanceList = "TRK_UNIT" + str(track_unit_number) + "_list"

		mLightInstanceList = "TRK_UNIT" + str(track_unit_number) + "_lightlist"
		mDynamicInstanceList = "TRK_UNIT" + str(track_unit_number) + "_dynlist"
		mPolygonSoupList = "TRK_COL_" + str(track_unit_number)
		mZoneHeader = "TRK_UNIT" + str(track_unit_number) + "_hdr"

		mLightInstanceListId = calculate_resourceid(mLightInstanceList.lower())
		mDynamicInstanceListId = calculate_resourceid(mDynamicInstanceList.lower())
		mPolygonSoupListId = calculate_resourceid(mPolygonSoupList.lower())
		mZoneHeaderId = calculate_resourceid(mZoneHeader.lower())

		lightinstancelist_path = os.path.join(lightinstancelist_dir, mLightInstanceListId + ".dat")
		dynamicinstancelist_path = os.path.join(dynamicinstancelist_dir, mDynamicInstanceListId + ".dat")
		polygonsouplist_path = os.path.join(polygonsouplist_dir, mPolygonSoupListId + ".dat")
		zoneheader_path = os.path.join(zoneheader_dir, mZoneHeaderId + ".dat")

		PolygonSoups = read_polygonsouplist(polygonsouplist_path, resource_version)

		instances_dynamic = read_dynamicinstancelist(dynamicinstancelist_path, worldobject_dir, shared_worldobject_dir, resource_version)
		instances += instances_dynamic

		lights = read_lightinstancelist(lightinstancelist_path, resource_version)

	elif resource_type == "GraphicsSpec":
		vehicle_name = decode_resource_id(mMainId, resource_type)
		mGraphicsSpec = str(vehicle_name) + "_Graphics"
		mGraphicsSpecId = mMainId
		mWheelGraphicsSpec = str(vehicle_name) + "_Wheels"
		mEffectsSpec = str(vehicle_name) + "_Effects"
		mCharacterSpec = str(vehicle_name) + "_Driver"
		instances, instances_wheel, instances_effects, mSkeletonId, mControlMeshId = read_graphicsspec(file_path, resource_version)

		mPolygonSoupList = "VEH_COL_" + str(vehicle_name)
		PolygonSoups = []

		# Skeleton
		mSkeleton = str(vehicle_name) + "_Skeleton"
		skeleton_path = os.path.join(skeleton_dir, mSkeletonId + ".dat")
		Skeleton = []
		if os.path.isfile(skeleton_path) == True:
			Skeleton = read_skeleton(skeleton_path, resource_version)

		# ControlMesh
		mControlMesh = str(vehicle_name) + "_ControlMesh"
		controlmesh_path = os.path.join(controlmesh_dir, mControlMeshId + "_16.dat")
		ControlMeshes = []
		if os.path.isfile(controlmesh_path) == True:
			ControlMeshes = read_controlmesh(controlmesh_path)

		# Driver coordinates
		genesysinstance_path = os.path.join(genesyinstance_dir, mGraphicsSpecId + ".dat")
		if os.path.isfile(genesysinstance_path):
			instance_character = read_genesysinstance_driver(genesyinstance_dir, genesysinstance_path, resource_version)

		# Proper wheel coordinates
		genesysinstance_path = os.path.join(genesyinstance_dir, mGraphicsSpecId + "_2.dat")
		for file in os.listdir(genesyinstance_dir):
			if mGraphicsSpecId in file and mGraphicsSpecId + '.dat' != file:
				genesysinstance_path = os.path.join(genesyinstance_dir, file)
				break

		if os.path.isfile(genesysinstance_path):
			instances_wheel = read_genesysinstance_wheels(genesyinstance_dir, genesysinstance_path, instances_wheel, resource_version)

	elif resource_type == "CharacterSpec":
		character_name = decode_resource_id(mMainId, resource_type)
		mCharacterSpec = str(character_name) + "_Graphics"
		mCharacterSpecId = mMainId
		instances, mSkeletonId, mAnimationListId = read_characterspec(file_path, resource_version)

		# Skeleton
		mSkeleton = str(character_name) + "_Skeleton"
		skeleton_path = os.path.join(skeleton_dir, mSkeletonId + ".dat")
		Skeleton = []
		if os.path.isfile(skeleton_path) == True:
			Skeleton = read_skeleton(skeleton_path, resource_version)

	elif resource_type == "Model":
		ModelId = os.path.basename(file_path).split(".")[0]
		instances = [[ModelId]]

	elif resource_type == "TriggerData":
		triggers = read_triggerdata(file_path, resource_version)

	elif resource_type == "ZoneList":
		zonelist = read_zonelist(file_path, resource_version)

	elif resource_type == "PolygonSoupList":
		world_collision = []
		track_unit_number = decode_resource_id(mMainId, resource_type)
		try:
			track_unit_number = int(track_unit_number.replace("TRK_COL_", ""))
			mPolygonSoupList = "TRK_COL_" + str(track_unit_number)
		except:
			mPolygonSoupList = "VEH_COL_" + mMainId
			track_unit_number = None

		PolygonSoups = read_polygonsouplist(file_path, resource_version)
		world_collision.append([track_unit_number, mPolygonSoupList, PolygonSoups])

	models_not_found = []
	for i in range(0, len(instances)):
		mModelId = instances[i][0]

		if mModelId in models:
			continue

		is_shared_asset = False

		model_path = os.path.join(model_dir, mModelId + ".dat")
		if not os.path.isfile(model_path):
			model_path = os.path.join(shared_model_dir, mModelId + ".dat")
			is_shared_asset = True
			if not os.path.isfile(model_path):
				print("WARNING: failed to open model %s: no such file in '%s' and '%s'. Ignoring it." % (mModelId, model_dir, shared_model_dir))
				models_not_found.append(i)
				continue

		model_properties, renderables_info = read_model(model_path, resource_version)
		models[mModelId] = [mModelId, [renderables_info, model_properties], is_shared_asset]

	for index in reversed(models_not_found):
		del instances[index]

	models_not_found = []
	for i in range(0, len(instances_wheel)):
		mModelId = instances_wheel[i][0]

		if mModelId in models:
			continue

		is_shared_asset = False

		model_path = os.path.join(model_dir, mModelId + ".dat")
		if not os.path.isfile(model_path):
			model_path = os.path.join(shared_model_dir, mModelId + ".dat")
			is_shared_asset = True
			if not os.path.isfile(model_path):
				print("WARNING: failed to open model %s: no such file in '%s' and '%s'. Ignoring it." % (mModelId, model_dir, shared_model_dir))
				models_not_found.append(i)
				continue

		model_properties, renderables_info = read_model(model_path, resource_version)
		models[mModelId] = [mModelId, [renderables_info, model_properties], is_shared_asset]

	for index in reversed(models_not_found):
		del instances_wheel[index]

	for model in models:
		for renderable_info in models[model][1][0]:
			mRenderableId = renderable_info[0]
			if mRenderableId in (rows[0] for rows in renderables):
				continue

			is_shared_asset = False

			renderable_path = os.path.join(renderable_dir, mRenderableId + ".dat")
			if not os.path.isfile(renderable_path):
				renderable_path = os.path.join(shared_renderable_dir, mRenderableId + ".dat")
				is_shared_asset = True
				if not os.path.isfile(renderable_path):
					print("WARNING: failed to open renderable %s: no such file in '%s' and '%s'." % (mRenderableId, renderable_dir, shared_renderable_dir))
					continue

			renderable_properties, meshes_info = read_renderable(renderable_path, resource_version)
			renderables.append([mRenderableId, [meshes_info, renderable_properties], is_shared_asset, renderable_path])

	for i in range(0, len(renderables)):
		for mesh_info in renderables[i][1][0]:
			mMaterialId = mesh_info[2]
			if mMaterialId in (rows[0] for rows in materials):
				continue

			is_shared_asset = False

			material_path = os.path.join(material_dir, mMaterialId + ".dat")
			if not os.path.isfile(material_path):
				material_path = os.path.join(shared_material_dir, mMaterialId + ".dat")
				is_shared_asset = True
				if not os.path.isfile(material_path):
					print("WARNING: failed to open material %s: no such file in '%s' and '%s'." % (mMaterialId, material_dir, shared_material_dir))
					continue

			material_properties, mShaderId, shader_type, sampler_states_info, textures_info, semantic_types = read_material(material_path, shared_shader_dir, resource_version)
			materials.append([mMaterialId, [mShaderId, shader_type, sampler_states_info, textures_info, material_properties, semantic_types], is_shared_asset])

	for i in range(0, len(materials)):
		mShaderId = materials[i][1][0]
		if mShaderId in (rows[0] for rows in shaders):
			continue

		shader_path = os.path.join(shared_shader_dir, mShaderId + "_83.dat")
		is_shared_asset = True
		if not os.path.isfile(shader_path):
			print("WARNING: failed to open shader %s: no such file in '%s'." % (mShaderId, shared_shader_dir))
			continue

		shader_type, mVertexDescriptorId, miNumSamplers, raster_types, shader_parameters, material_constants, texture_samplers, vertex_properties = read_shader(shader_path, resource_version)
		shaders.append([mShaderId, [raster_types], shader_type, mVertexDescriptorId, miNumSamplers, raster_types,
						shader_parameters, material_constants, texture_samplers, vertex_properties, is_shared_asset])

	for i in range(0, len(materials)):
		for textures_info in materials[i][1][3]:
			mTextureId = textures_info[0]
			if mTextureId in (rows[0] for rows in rasters):
				continue

			is_shared_asset = False

			texture_path = os.path.join(raster_dir, mTextureId + ".dat")
			if not os.path.isfile(texture_path):
				texture_path = os.path.join(shared_raster_dir, mTextureId + ".dat")
				is_shared_asset = True
				if not os.path.isfile(texture_path):
					texture_path = os.path.join(shared_raster_dir, mTextureId + ".dds")
					if not os.path.isfile(texture_path):
						print("WARNING: failed to open texture %s from material %s: no such file in '%s' and '%s'." % (mTextureId, materials[i][0], raster_dir, shared_raster_dir))
						continue

			texture_properties = read_texture(texture_path, resource_version)
			rasters.append([mTextureId, [texture_properties], is_shared_asset, texture_path])

	# Model textures
	if resource_type == "InstanceList":
		for model in models:
			if models[model][1][1][3] == True:
				textures = models[model][1][1][8]
				for mTextureId in textures:
					if mTextureId in (rows[0] for rows in rasters):
						continue

					is_shared_asset = False

					texture_path = os.path.join(raster_dir, mTextureId + ".dat")
					if not os.path.isfile(texture_path):
						texture_path = os.path.join(shared_raster_dir, mTextureId + ".dat")
						is_shared_asset = True
						if not os.path.isfile(texture_path):
							texture_path = os.path.join(shared_raster_dir, mTextureId + ".dds")
							if not os.path.isfile(texture_path):
								print("WARNING: failed to open texture %s from model %s: no such file in '%s' and '%s'." % (mTextureId, model, raster_dir, shared_raster_dir))
								continue

					texture_properties = read_texture(texture_path, resource_version)
					rasters.append([mTextureId, [texture_properties], is_shared_asset, texture_path])

	elapsed_time = time.time() - parsing_time
	print("... %.4fs" % elapsed_time)

	## IMPORTING TO SCENE
	print("Importing data to scene...")
	importing_time = time.time()

	# Main file
	#main_collection_name = os.path.splitext(os.path.basename(file_path))[0]
	main_collection_name = main_collection_name
	if resource_type == "PolygonSoupList":
		main_collection_name = "COLLISION"

	if resource_type == "PolygonSoupList":
		main_collection = bpy.data.collections.get(main_collection_name)
		if main_collection == None:
			main_collection = bpy.data.collections.new(main_collection_name)
			bpy.context.scene.collection.children.link(main_collection)
			main_collection["resource_type"] = resource_type
			main_collection.color_tag = "COLOR_01"
	else:
		main_collection = bpy.data.collections.new(main_collection_name)
		bpy.context.scene.collection.children.link(main_collection)
		main_collection["resource_type"] = resource_type
		main_collection.color_tag = "COLOR_01"

	if resource_type == "InstanceList":
		instancelist_collection = bpy.data.collections.new(mInstanceList)
		instancelist_collection["resource_type"] = "InstanceList"
		instancelist_collection.color_tag = "COLOR_02"
		main_collection.children.link(instancelist_collection)

		polygonsouplist_collection = bpy.data.collections.new(mPolygonSoupList)
		polygonsouplist_collection["resource_type"] = "PolygonSoupList"
		polygonsouplist_collection.color_tag = "COLOR_03"
		main_collection.children.link(polygonsouplist_collection)

		dynamic_collection = bpy.data.collections.new(mDynamicInstanceList)
		dynamic_collection["resource_type"] = "DynamicInstanceList"
		dynamic_collection.color_tag = "COLOR_05"
		main_collection.children.link(dynamic_collection)

		lightinstancelist_collection = bpy.data.collections.new(mLightInstanceList)
		lightinstancelist_collection["resource_type"] = "LightInstanceList"
		lightinstancelist_collection.color_tag = "COLOR_07"
		main_collection.children.link(lightinstancelist_collection)

		if hide_polygonsoup == True:
			bpy.context.view_layer.layer_collection.children.get(main_collection.name).children.get(polygonsouplist_collection.name).hide_viewport = True

	elif resource_type == "GraphicsSpec":
		graphicsspec_collection = bpy.data.collections.new(mGraphicsSpec)
		graphicsspec_collection["resource_type"] = "GraphicsSpec"
		graphicsspec_collection.color_tag = "COLOR_02"
		main_collection.children.link(graphicsspec_collection)

		wheelgraphicspec_collection = bpy.data.collections.new(mWheelGraphicsSpec)
		wheelgraphicspec_collection["resource_type"] = "WheelGraphicsSpec"
		wheelgraphicspec_collection.color_tag = "COLOR_03"
		main_collection.children.link(wheelgraphicspec_collection)

		# if len(Skeleton) > 0:
			# skeleton_collection = bpy.data.collections.new(mSkeleton)
			# skeleton_collection["resource_type"] = "Skeleton"
			# skeleton_collection["SkeletonID"] = mSkeletonId
			# main_collection["SkeletonID"] = mSkeletonId
			# skeleton_collection.color_tag = "COLOR_07"
			# main_collection.children.link(skeleton_collection)

		if len(Skeleton) > 0:
			skeleton_collection2 = bpy.data.collections.new(mSkeleton)
			skeleton_collection2["resource_type"] = "Skeleton"
			#skeleton_collection2["SkeletonID"] = mSkeletonId
			#main_collection["SkeletonID"] = mSkeletonId
			skeleton_collection2.color_tag = "COLOR_07"
			main_collection.children.link(skeleton_collection2)

		if len(ControlMeshes) > 0:
			controlmesh_collection = bpy.data.collections.new(mControlMesh)
			controlmesh_collection["resource_type"] = "ControlMesh"
			#controlmesh_collection["ControlMeshID"] = mControlMeshId
			#main_collection["ControlMeshID"] = mControlMeshId
			controlmesh_collection.color_tag = "COLOR_08"
			main_collection.children.link(controlmesh_collection)

		effects_collection = bpy.data.collections.new(mEffectsSpec)
		effects_collection["resource_type"] = "Effects"
		effects_collection.color_tag = "COLOR_05"
		main_collection.children.link(effects_collection)

		if len(instance_character) > 0:
			character_collection = bpy.data.collections.new(mCharacterSpec)
			character_collection["resource_type"] = "Character"
			character_collection.color_tag = "COLOR_06"
			main_collection.children.link(character_collection)

		# if hide_skeleton == True and len(Skeleton) > 0:
			# bpy.context.view_layer.layer_collection.children.get(main_collection.name).children.get(skeleton_collection.name).hide_viewport = True

		if hide_skeleton == True and len(Skeleton) > 0:
			bpy.context.view_layer.layer_collection.children.get(main_collection.name).children.get(skeleton_collection2.name).hide_viewport = True

		if hide_controlmesh == True and len(ControlMeshes) > 0:
			bpy.context.view_layer.layer_collection.children.get(main_collection.name).children.get(controlmesh_collection.name).hide_viewport = True

		if hide_effects == True:
			bpy.context.view_layer.layer_collection.children.get(main_collection.name).children.get(effects_collection.name).hide_viewport = True

	elif resource_type == "CharacterSpec":
		characterspec_collection = bpy.data.collections.new(mCharacterSpec)
		characterspec_collection["resource_type"] = "CharacterSpec"
		main_collection["AnimationListID"] = mAnimationListId
		characterspec_collection.color_tag = "COLOR_02"
		main_collection.children.link(characterspec_collection)

		# if len(Skeleton) > 0:
			# skeleton_collection = bpy.data.collections.new(mSkeleton)
			# skeleton_collection["resource_type"] = "Skeleton"
			# #skeleton_collection["SkeletonId"] = mSkeletonId
			# main_collection["SkeletonID"] = mSkeletonId
			# skeleton_collection.color_tag = "COLOR_07"
			# main_collection.children.link(skeleton_collection)

		if len(Skeleton) > 0:
			skeleton_collection2 = bpy.data.collections.new(mSkeleton)
			skeleton_collection2["resource_type"] = "Skeleton"
			main_collection["SkeletonID"] = mSkeletonId
			skeleton_collection2.color_tag = "COLOR_07"
			main_collection.children.link(skeleton_collection2)

		# if hide_skeleton == True and len(Skeleton) > 0:
			# bpy.context.view_layer.layer_collection.children.get(main_collection.name).children.get(skeleton_collection.name).hide_viewport = True

		if hide_skeleton == True and len(Skeleton) > 0:
			bpy.context.view_layer.layer_collection.children.get(main_collection.name).children.get(skeleton_collection2.name).hide_viewport = True

	elif resource_type == "TriggerData":
		boxtrigger_collection = bpy.data.collections.new("BoxTriggers")
		boxtrigger_collection["resource_type"] = "TriggerData"
		boxtrigger_collection.color_tag = "COLOR_02"
		main_collection.children.link(boxtrigger_collection)

		spheretrigger_collection = bpy.data.collections.new("SphereTriggers")
		spheretrigger_collection["resource_type"] = "TriggerData"
		spheretrigger_collection.color_tag = "COLOR_03"
		main_collection.children.link(spheretrigger_collection)

		locatortrigger_collection = bpy.data.collections.new("LocatorTriggers")
		locatortrigger_collection["resource_type"] = "TriggerData"
		locatortrigger_collection.color_tag = "COLOR_04"
		main_collection.children.link(locatortrigger_collection)

		celltrigger_collection = bpy.data.collections.new("CellTriggers")
		celltrigger_collection["resource_type"] = "TriggerData"
		celltrigger_collection.color_tag = "COLOR_05"
		main_collection.children.link(celltrigger_collection)

	elif resource_type == "ZoneList":
		zonelist_collection = bpy.data.collections.new("ZoneList")
		zonelist_collection["resource_type"] = "ZoneList"
		zonelist_collection.color_tag = "COLOR_03"
		main_collection.children.link(zonelist_collection)

	elif resource_type == "PolygonSoupList":
		for collision in world_collision:
			track_unit_number, mPolygonSoupList, PolygonSoups = collision
			polygonsouplist_collection = bpy.data.collections.new(collision[1])
			polygonsouplist_collection["resource_type"] = "PolygonSoupList"
			polygonsouplist_collection.color_tag = "COLOR_04"
			main_collection.children.link(polygonsouplist_collection)
			collision.append(polygonsouplist_collection)

	for raster in rasters:
		raster_path = raster[-1]
		texture_properties = raster[1][0]
		is_shared_asset = raster[2]
		ext = os.path.splitext(raster_path)[1]

		raster_path = create_texture(raster_path, texture_properties)
		#if not "DXT" in texture_properties[0]:
		#	print("WARNING: converting texture %s DXT compression from '%s' to 'DXT5'. Blender can not handle well the original compression." % (os.path.splitext(os.path.basename(raster_path))[0], texture_properties[0]))
		#	raster_path = convert_texture_to_dxt5(raster_path, True)
		raster_image = bpy.data.images.load(raster_path, check_existing = True)
		raster_image.name = raster[0]

		raster_image["is_shared_asset"] = is_shared_asset
		if ext == ".dds":
			continue
		format, width, height, depth, dimension, main_mipmap, mipmap, unknown_0x20 = texture_properties
		raster_image["dimension"] = dimension
		raster_image["main_mipmap"] = main_mipmap
		raster_image["flags"] = unknown_0x20

		if is_bundle == True:
			raster_image.pack()

	if random_color == True:
		RGBA_random = get_random_color()
		RGBA_random2 = get_random_color()

	for material in materials:
		if bpy.data.materials.get(material[0]) is None:
			mMaterialId = material[0]
			mShaderId = material[1][0]
			shader_type = material[1][1]
			sampler_states_info = material[1][2]
			textures_info = material[1][3]
			material_properties = material[1][4]
			parameters_Data, parameters_Names = material_properties[0]
			is_shared_asset = material[2]
			#raster_types = {}

			#if shader[6][3] != len(parameters_Data):
			#	print("WARNING: parameters_Data is different between material %s and shader %s." %(mMaterialId, mShaderId))

			mat = bpy.data.materials.new(mMaterialId)
			mat.use_nodes = True
			mat.name = mMaterialId

			if mat.node_tree.nodes[0].bl_idname != "ShaderNodeOutputMaterial":
				mat.node_tree.nodes[0].name = mMaterialId

			# Color
			material_color = []
			if "materialDiffuse" in parameters_Names:
				material_color = parameters_Data[parameters_Names.index("materialDiffuse")]
			elif "mMaterialDiffuse" in parameters_Names:
				material_color = parameters_Data[parameters_Names.index("mMaterialDiffuse")]

			if material_color != []:
				mat.node_tree.nodes[mMaterialId].inputs['Base Color'].default_value = material_color

			# Textures
			if len(textures_info) > 0:
				uv_map_node0 = mat.node_tree.nodes.new(type='ShaderNodeUVMap')
				if "TEXCOORD1" in semantic_types:
					uv_map_node0.uv_map = "UVMap"
				elif "TEXCOORD2" in semantic_types:
					uv_map_node0.uv_map = "UV2Map"
				elif "TEXCOORD3" in semantic_types:
					uv_map_node0.uv_map = "UV3Map"
				elif "TEXCOORD4" in semantic_types:
					uv_map_node0.uv_map = "UV4Map"
				elif "TEXCOORD5" in semantic_types:
					uv_map_node0.uv_map = "UV5Map"
				for i in range(0, len(textures_info)):
					mTextureId = textures_info[i][0]
					texture_type = textures_info[i][1]
					#try:
					#	texture_type = raster_types[texture_sampler_code]
					#except:
					#	print("WARNING: raster type (channel) not defined by shader %s, found in material %s. It is defined as %d" % (mShaderId, mMaterialId, texture_sampler_code))
					#	texture_type = "Undefined"

					mat_tex = mat.node_tree.nodes.new('ShaderNodeTexImage')
					mat_tex.image = bpy.data.images.get(mTextureId)
					mat_tex.name = texture_type
					mat_tex.label = mTextureId
					mat_tex["is_shared_asset"] = is_shared_asset
					if texture_type == "DiffuseTextureSampler":
						mat.node_tree.links.new(mat.node_tree.nodes[mMaterialId].inputs['Base Color'], mat_tex.outputs['Color'])
					elif texture_type == "SpecularTextureSampler":
						mat.node_tree.links.new(mat.node_tree.nodes[mMaterialId].inputs['Specular'], mat_tex.outputs['Color'])
					elif texture_type == "NormalTextureSampler" or "Normal" in texture_type:
						if not mat_tex.image is None:
							mat_tex.image.colorspace_settings.name = "Non-Color"
					elif texture_type == "AoMapTextureSampler":
						if not mat_tex.image is None:
							mat_tex.image.colorspace_settings.name = "Non-Color"

					mat.node_tree.links.new(uv_map_node0.outputs['UV'], mat_tex.inputs['Vector'])

				try:
					NormalTextureSampler_tex = mat.node_tree.nodes['NormalTextureSampler']

					normal_map_node1 = mat.node_tree.nodes.new(type='ShaderNodeNormalMap')
					normal_map_node1.uv_map = "UVMap"

					mat.node_tree.links.new(NormalTextureSampler_tex.outputs['Color'], normal_map_node1.inputs['Color'])
					mat.node_tree.links.new(normal_map_node1.outputs['Normal'], mat.node_tree.nodes[mMaterialId].inputs['Normal'])
				except:
					pass

				skip_shading = False
				if skip_shading == True:
					print("WARNING: skipping shading.")
					pass

				# Vehicles
				elif shader_type == "Vehicle_1Bit_Textured_NormalMapped_Emissive_AO_Livery":
					DiffuseTextureSampler_tex = mat.node_tree.nodes['DiffuseTextureSampler']
					NormalTextureSampler_tex = mat.node_tree.nodes['NormalTextureSampler']

					materialDiffuse = parameters_Data[parameters_Names.index("materialDiffuse")]

					mix_rgb_node = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					uv_map_node1 = mat.node_tree.nodes.new(type='ShaderNodeUVMap')
					normal_map_node1 = mat.node_tree.nodes.new(type='ShaderNodeNormalMap')

					mix_rgb_node.inputs['Color1'].default_value = materialDiffuse
					mix_rgb_node.blend_type = "OVERLAY"
					uv_map_node1.uv_map = "UV3Map"
					normal_map_node1.uv_map = "UV3Map"
					normal_map_node1.inputs['Strength'].default_value = 0.15

					mat.node_tree.links.new(uv_map_node1.outputs['UV'], DiffuseTextureSampler_tex.inputs['Vector'])
					mat.node_tree.links.new(uv_map_node1.outputs['UV'], NormalTextureSampler_tex.inputs['Vector'])

					mat.node_tree.links.new(DiffuseTextureSampler_tex.outputs['Alpha'], mix_rgb_node.inputs['Fac'])
					mat.node_tree.links.new(DiffuseTextureSampler_tex.outputs['Color'], mix_rgb_node.inputs['Color2'])
					mat.node_tree.links.new(mix_rgb_node.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Base Color'])

					mat.node_tree.links.new(NormalTextureSampler_tex.outputs['Color'], normal_map_node1.inputs['Color'])
					mat.node_tree.links.new(normal_map_node1.outputs['Normal'], mat.node_tree.nodes[mMaterialId].inputs['Normal'])

					mat.node_tree.links.new(DiffuseTextureSampler_tex.outputs['Alpha'], mat.node_tree.nodes[mMaterialId].inputs['Alpha'])
					mat.blend_method = 'BLEND'
					mat.shadow_method = 'HASHED'
					mat.use_backface_culling = True

				elif shader_type == "Vehicle_1Bit_Textured_Normalmapped_Reflective":
					DiffuseTextureSampler_tex = mat.node_tree.nodes['DiffuseTextureSampler']
					NormalTextureSampler_tex = mat.node_tree.nodes['NormalTextureSampler']

					normal_map_node1 = mat.node_tree.nodes.new(type='ShaderNodeNormalMap')
					normal_map_node1.uv_map = "UVMap"

					#mat.node_tree.links.new(NormalTextureSampler_tex.outputs['Color'], normal_map_node1.inputs['Color'])
					#mat.node_tree.links.new(normal_map_node1.outputs['Normal'], mat.node_tree.nodes[mMaterialId].inputs['Normal'])
					mat.node_tree.links.new(NormalTextureSampler_tex.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Normal'])

					mat.node_tree.links.new(DiffuseTextureSampler_tex.outputs['Alpha'], mat.node_tree.nodes[mMaterialId].inputs['Alpha'])
					mat.blend_method = 'BLEND'
					mat.shadow_method = 'HASHED'

					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.5
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 0.2

				elif shader_type == "Vehicle_1Bit_Textured_NormalMapped_Reflective_Emissive_AO_Livery":
					DiffuseTextureSampler_tex = mat.node_tree.nodes['DiffuseTextureSampler']
					NormalTextureSampler_tex = mat.node_tree.nodes['NormalTextureSampler']

					materialDiffuse = parameters_Data[parameters_Names.index("materialDiffuse")]

					mix_rgb_node = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					uv_map_node1 = mat.node_tree.nodes.new(type='ShaderNodeUVMap')
					normal_map_node1 = mat.node_tree.nodes.new(type='ShaderNodeNormalMap')

					mix_rgb_node.inputs['Color1'].default_value = materialDiffuse
					mix_rgb_node.blend_type = "OVERLAY"
					uv_map_node1.uv_map = "UV3Map"
					normal_map_node1.uv_map = "UV3Map"
					normal_map_node1.inputs['Strength'].default_value = 0.15

					mat.node_tree.links.new(uv_map_node1.outputs['UV'], DiffuseTextureSampler_tex.inputs['Vector'])
					mat.node_tree.links.new(uv_map_node1.outputs['UV'], NormalTextureSampler_tex.inputs['Vector'])

					mat.node_tree.links.new(DiffuseTextureSampler_tex.outputs['Alpha'], mix_rgb_node.inputs['Fac'])
					mat.node_tree.links.new(DiffuseTextureSampler_tex.outputs['Color'], mix_rgb_node.inputs['Color2'])
					mat.node_tree.links.new(mix_rgb_node.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Base Color'])

					mat.node_tree.links.new(NormalTextureSampler_tex.outputs['Color'], normal_map_node1.inputs['Color'])
					mat.node_tree.links.new(normal_map_node1.outputs['Normal'], mat.node_tree.nodes[mMaterialId].inputs['Normal'])

					mat.node_tree.links.new(DiffuseTextureSampler_tex.outputs['Alpha'], mat.node_tree.nodes[mMaterialId].inputs['Alpha'])

					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.5
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 0.25

					mat.blend_method = 'HASHED'
					mat.shadow_method = 'HASHED'

				elif shader_type == "Vehicle_Glass_Coloured":
					mGlassColour = parameters_Data[parameters_Names.index("mGlassColour")]
					mGlassControls = parameters_Data[parameters_Names.index("mGlassControls")]

					mat.node_tree.nodes[mMaterialId].inputs['Base Color'].default_value = mGlassColour

					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.0
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 0.0
					mat.node_tree.nodes[mMaterialId].inputs['Transmission'].default_value = 1.0
					mat.node_tree.nodes[mMaterialId].inputs['Alpha'].default_value = 1.0 - mGlassControls[3]

					mat.use_screen_refraction = True
					mat.refraction_depth = 0.01

					mat.use_backface_culling = False

					mat.blend_method = 'BLEND'
					mat.shadow_method = 'HASHED'
					mat.show_transparent_back = False

					bpy.context.scene.eevee.use_ssr = True
					bpy.context.scene.eevee.use_ssr_refraction = True

				elif shader_type == "Vehicle_Glass_Emissive_Coloured":
					mGlassColour = parameters_Data[parameters_Names.index("mGlassColour")]
					mGlassControls = parameters_Data[parameters_Names.index("mGlassControls")]

					mat.node_tree.nodes[mMaterialId].inputs['Base Color'].default_value = mGlassColour

					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.0
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 0.0
					mat.node_tree.nodes[mMaterialId].inputs['Transmission'].default_value = 1.0
					mat.node_tree.nodes[mMaterialId].inputs['Alpha'].default_value = 1.0 - mGlassControls[3]

					mat.use_screen_refraction = True
					mat.refraction_depth = 0.01

					#mat.use_backface_culling = True

					mat.blend_method = 'BLEND'
					mat.shadow_method = 'HASHED'
					mat.show_transparent_back = False

					bpy.context.scene.eevee.use_ssr = True
					bpy.context.scene.eevee.use_ssr_refraction = True

				elif shader_type == "Vehicle_Glass_Emissive_Coloured_Wrap":
					mGlassColour = parameters_Data[parameters_Names.index("mGlassColour")]
					mGlassControls = parameters_Data[parameters_Names.index("mGlassControls")]

					mat.node_tree.nodes[mMaterialId].inputs['Base Color'].default_value = mGlassColour

					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.0
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 0.0
					mat.node_tree.nodes[mMaterialId].inputs['Transmission'].default_value = 1.0
					mat.node_tree.nodes[mMaterialId].inputs['Alpha'].default_value = 1.0 - mGlassControls[3]

					mat.use_screen_refraction = True
					mat.refraction_depth = 0.01

					mat.use_backface_culling = False

					mat.blend_method = 'BLEND'
					mat.shadow_method = 'HASHED'
					mat.show_transparent_back = False

					bpy.context.scene.eevee.use_ssr = True
					bpy.context.scene.eevee.use_ssr_refraction = True

				elif shader_type == "Vehicle_Glass_Emissive_Coloured_Singlesided":
					mGlassColour = parameters_Data[parameters_Names.index("mGlassColour")]
					mGlassControls = parameters_Data[parameters_Names.index("mGlassControls")]

					mat.node_tree.nodes[mMaterialId].inputs['Base Color'].default_value = mGlassColour

					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.0
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 0.0
					mat.node_tree.nodes[mMaterialId].inputs['Transmission'].default_value = 1.0
					mat.node_tree.nodes[mMaterialId].inputs['Alpha'].default_value = 1.0 - mGlassControls[3]

					mat.use_screen_refraction = True
					mat.refraction_depth = 0.01

					mat.use_backface_culling = True

					mat.blend_method = 'BLEND'
					mat.shadow_method = 'HASHED'
					mat.show_transparent_back = False

					bpy.context.scene.eevee.use_ssr = True
					bpy.context.scene.eevee.use_ssr_refraction = True

				elif shader_type == "Vehicle_Glass_Emissive_Coloured_Singlesided_Wrap":
					mGlassColour = parameters_Data[parameters_Names.index("mGlassColour")]
					mGlassControls = parameters_Data[parameters_Names.index("mGlassControls")]

					mat.node_tree.nodes[mMaterialId].inputs['Base Color'].default_value = mGlassColour

					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.0
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 0.0
					mat.node_tree.nodes[mMaterialId].inputs['Transmission'].default_value = 1.0
					mat.node_tree.nodes[mMaterialId].inputs['Alpha'].default_value = 1.0 - mGlassControls[3]

					mat.use_screen_refraction = True
					mat.refraction_depth = 0.01

					mat.use_backface_culling = True

					mat.blend_method = 'BLEND'
					mat.shadow_method = 'HASHED'
					mat.show_transparent_back = False

					bpy.context.scene.eevee.use_ssr = True
					bpy.context.scene.eevee.use_ssr_refraction = True

				elif shader_type == "Vehicle_Glass_LocalEmissive_Coloured":
					mGlassColour = parameters_Data[parameters_Names.index("mGlassColour")]
					mGlassControls = parameters_Data[parameters_Names.index("mGlassControls")]
					gEmissiveColour = parameters_Data[parameters_Names.index("gEmissiveColour")]
					mSelfIlluminationMultiplier = parameters_Data[parameters_Names.index("mSelfIlluminationMultiplier")]

					mat.node_tree.nodes[mMaterialId].inputs['Base Color'].default_value = mGlassColour
					mat.node_tree.nodes[mMaterialId].inputs['Emission'].default_value = gEmissiveColour
					mat.node_tree.nodes[mMaterialId].inputs['Emission Strength'].default_value = mSelfIlluminationMultiplier[0]*10.0

					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.0
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 0.0
					mat.node_tree.nodes[mMaterialId].inputs['Transmission'].default_value = 1.0
					mat.node_tree.nodes[mMaterialId].inputs['Alpha'].default_value = 1.0 - mGlassControls[3]

					mat.use_screen_refraction = True
					mat.refraction_depth = 0.01

					#mat.use_backface_culling = True

					mat.blend_method = 'BLEND'
					mat.shadow_method = 'HASHED'
					mat.show_transparent_back = False

					bpy.context.scene.eevee.use_ssr = True
					bpy.context.scene.eevee.use_ssr_refraction = True

				elif shader_type == "Vehicle_Greyscale_Textured_Normalmapped":
					DiffuseTextureSampler_tex = mat.node_tree.nodes['DiffuseTextureSampler']
					NormalTextureSampler_tex = mat.node_tree.nodes['NormalTextureSampler']

					materialDiffuse = parameters_Data[parameters_Names.index("materialDiffuse")]

					mix_rgb_node = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')

					mix_rgb_node.blend_type = "OVERLAY"
					mix_rgb_node.inputs['Color1'].default_value = materialDiffuse

					normal_map_node1 = mat.node_tree.nodes.new(type='ShaderNodeNormalMap')
					normal_map_node1.uv_map = "UVMap"

					mat.node_tree.links.new(NormalTextureSampler_tex.outputs['Color'], normal_map_node1.inputs['Color'])
					mat.node_tree.links.new(normal_map_node1.outputs['Normal'], mat.node_tree.nodes[mMaterialId].inputs['Normal'])

					mat.node_tree.links.new(DiffuseTextureSampler_tex.outputs['Alpha'], mix_rgb_node.inputs['Fac'])
					mat.node_tree.links.new(DiffuseTextureSampler_tex.outputs['Color'], mix_rgb_node.inputs['Color2'])
					mat.node_tree.links.new(mix_rgb_node.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Base Color'])

					mat.node_tree.links.new(DiffuseTextureSampler_tex.outputs['Alpha'], mat.node_tree.nodes[mMaterialId].inputs['Alpha'])

					mat.blend_method = 'BLEND'
					mat.shadow_method = 'HASHED'

				elif shader_type == "Vehicle_Greyscale_Textured_Normalmapped_Reflective":
					DiffuseTextureSampler_tex = mat.node_tree.nodes['DiffuseTextureSampler']
					NormalTextureSampler_tex = mat.node_tree.nodes['NormalTextureSampler']

					normal_map_node1 = mat.node_tree.nodes.new(type='ShaderNodeNormalMap')
					normal_map_node1.uv_map = "UVMap"

					#mat.node_tree.links.new(NormalTextureSampler_tex.outputs['Color'], normal_map_node1.inputs['Color'])
					#mat.node_tree.links.new(normal_map_node1.outputs['Normal'], mat.node_tree.nodes[mMaterialId].inputs['Normal'])
					mat.node_tree.links.new(NormalTextureSampler_tex.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Normal'])

					mat.node_tree.links.new(DiffuseTextureSampler_tex.outputs['Alpha'], mat.node_tree.nodes[mMaterialId].inputs['Alpha'])
					mat.blend_method = 'BLEND'
					mat.shadow_method = 'HASHED'

					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.5
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 0.2

				elif shader_type == "Vehicle_Opaque_Emissive_AO":
					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.0
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 0.5

				elif shader_type == "Vehicle_Opaque_Emissive_Reflective_AO":
					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.9
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 0.2

				elif shader_type == "Vehicle_Opaque_PaintGloss_Textured_LightmappedLights":
					mPaintColourIndex = parameters_Data[parameters_Names.index("mPaintColourIndex")][0]
					if random_color == True:
						if mPaintColourIndex == 0:
							mat.node_tree.nodes[mMaterialId].inputs['Base Color'].default_value = RGBA_random
						else:
							mat.node_tree.nodes[mMaterialId].inputs['Base Color'].default_value = RGBA_random2
					else:
						if mPaintColourIndex == 0:
							mat.node_tree.nodes[mMaterialId].inputs['Base Color'].default_value = (0.8, 0.8, 0.8, 1.0)
						else:
							mat.node_tree.nodes[mMaterialId].inputs['Base Color'].default_value = (1.0, 0.132868, 0.0, 1.0)
					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.75
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 0.25

				elif shader_type == "Vehicle_Opaque_PaintGloss_Textured_LightmappedLights_Wrap":
					mPaintColourIndex = parameters_Data[parameters_Names.index("mPaintColourIndex")][0]
					if random_color == True:
						if mPaintColourIndex == 0:
							mat.node_tree.nodes[mMaterialId].inputs['Base Color'].default_value = RGBA_random
						else:
							mat.node_tree.nodes[mMaterialId].inputs['Base Color'].default_value = RGBA_random2
					else:
						if mPaintColourIndex == 0:
							mat.node_tree.nodes[mMaterialId].inputs['Base Color'].default_value = (0.8, 0.8, 0.8, 1.0)
						else:
							mat.node_tree.nodes[mMaterialId].inputs['Base Color'].default_value = (1.0, 0.132868, 0.0, 1.0)
					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.75
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 0.25

				elif shader_type == "Vehicle_Opaque_PaintGloss_Textured_LightmappedLights_ColourOverride":
					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.75
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 0.25

				elif shader_type == "Vehicle_Opaque_PaintGloss_Textured_LightmappedLights_ColourOverride_Wrap":
					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.75
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 0.25

				elif shader_type == "Vehicle_Opaque_PaintGloss_Textured_LightmappedLights_ColourOverride_Livery":
					DiffuseTextureSampler_tex = mat.node_tree.nodes['DiffuseTextureSampler']

					uv_map_node1 = mat.node_tree.nodes.new(type='ShaderNodeUVMap')
					uv_map_node1.uv_map = "UV3Map"

					if sampler_states_info[0][0] == 'AD_42_2A_75':
						DiffuseTextureSampler_tex.extension = "EXTEND"

					mat.node_tree.links.new(uv_map_node1.outputs['UV'], DiffuseTextureSampler_tex.inputs['Vector'])

					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.75
					mat.node_tree.nodes[mMaterialId].inputs['Specular'].default_value = 0.2
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 0.25

				elif shader_type == "Vehicle_Opaque_PaintGloss_Textured_LightmappedLights_Livery":
					DiffuseTextureSampler_tex = mat.node_tree.nodes['DiffuseTextureSampler']

					mPaintColourIndex = parameters_Data[parameters_Names.index("mPaintColourIndex")][0]

					mix_rgb_node = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					uv_map_node1 = mat.node_tree.nodes.new(type='ShaderNodeUVMap')

					mix_rgb_node.blend_type = "MIX"
					uv_map_node1.uv_map = "UV3Map"

					DiffuseTextureSampler_tex.extension = "EXTEND"

					if random_color == True:
						if mPaintColourIndex == 0:
							mix_rgb_node.inputs['Color1'].default_value = RGBA_random
						else:
							mix_rgb_node.inputs['Color1'].default_value = RGBA_random2
					else:
						if mPaintColourIndex == 0:
							mix_rgb_node.inputs['Color1'].default_value = (0.8, 0.8, 0.8, 1.0)
						else:
							mix_rgb_node.inputs['Color1'].default_value = (1.0, 0.132868, 0.0, 1.0)

					mat.node_tree.links.new(uv_map_node1.outputs['UV'], DiffuseTextureSampler_tex.inputs['Vector'])
					mat.node_tree.links.new(DiffuseTextureSampler_tex.outputs['Alpha'], mix_rgb_node.inputs['Fac'])
					mat.node_tree.links.new(DiffuseTextureSampler_tex.outputs['Color'], mix_rgb_node.inputs['Color2'])
					mat.node_tree.links.new(mix_rgb_node.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Base Color'])

					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.75
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 0.25

				elif shader_type == "Vehicle_Opaque_PaintGloss_Textured_LightmappedLights_Livery_Wrap":
					DiffuseTextureSampler_tex = mat.node_tree.nodes['DiffuseTextureSampler']

					mPaintColourIndex = parameters_Data[parameters_Names.index("mPaintColourIndex")][0]

					mix_rgb_node = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					uv_map_node1 = mat.node_tree.nodes.new(type='ShaderNodeUVMap')

					mix_rgb_node.blend_type = "MIX"
					uv_map_node1.uv_map = "UV3Map"

					DiffuseTextureSampler_tex.extension = "EXTEND"

					if random_color == True:
						if mPaintColourIndex == 0:
							mix_rgb_node.inputs['Color1'].default_value = RGBA_random
						else:
							mix_rgb_node.inputs['Color1'].default_value = RGBA_random2
					else:
						if mPaintColourIndex == 0:
							mix_rgb_node.inputs['Color1'].default_value = (0.8, 0.8, 0.8, 1.0)
						else:
							mix_rgb_node.inputs['Color1'].default_value = (1.0, 0.132868, 0.0, 1.0)

					mat.node_tree.links.new(uv_map_node1.outputs['UV'], DiffuseTextureSampler_tex.inputs['Vector'])
					mat.node_tree.links.new(DiffuseTextureSampler_tex.outputs['Alpha'], mix_rgb_node.inputs['Fac'])
					mat.node_tree.links.new(DiffuseTextureSampler_tex.outputs['Color'], mix_rgb_node.inputs['Color2'])
					mat.node_tree.links.new(mix_rgb_node.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Base Color'])

					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.75
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 0.25

				elif shader_type == "Vehicle_Opaque_Textured":
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 0.3
					mat.use_backface_culling = True

				elif shader_type == "Vehicle_Opaque_Textured_Normalmapped_AO":
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 0.7

				elif shader_type == "Vehicle_Opaque_Textured_NormalMapped_Emissive_AO":
					LightmapLightsTextureSampler_tex = mat.node_tree.nodes['LightmapLightsTextureSampler']

					mSelfIlluminationMultiplier = parameters_Data[parameters_Names.index("mSelfIlluminationMultiplier")]
					LightmappedLightsRedChannelColour   = parameters_Data[parameters_Names.index("LightmappedLightsRedChannelColour")]
					LightmappedLightsGreenChannelColour = parameters_Data[parameters_Names.index("LightmappedLightsGreenChannelColour")]
					LightmappedLightsBlueChannelColour  = parameters_Data[parameters_Names.index("LightmappedLightsBlueChannelColour")]

					separate_rgb_node1 = mat.node_tree.nodes.new(type='ShaderNodeSeparateRGB')
					mix_rgb_node_r = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					mix_rgb_node_g = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					mix_rgb_node_b = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					mix_rgb_node1 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					mix_rgb_node2 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')

					mix_rgb_node_r.inputs['Color1'].default_value = (0, 0, 0, 0)
					mix_rgb_node_g.inputs['Color1'].default_value = (0, 0, 0, 0)
					mix_rgb_node_b.inputs['Color1'].default_value = (0, 0, 0, 0)

					mix_rgb_node_r.inputs['Color2'].default_value = LightmappedLightsRedChannelColour
					mix_rgb_node_g.inputs['Color2'].default_value = LightmappedLightsGreenChannelColour
					mix_rgb_node_b.inputs['Color2'].default_value = LightmappedLightsBlueChannelColour

					mat.node_tree.links.new(LightmapLightsTextureSampler_tex.outputs['Color'], separate_rgb_node1.inputs['Image'])

					mat.node_tree.links.new(separate_rgb_node1.outputs['R'], mix_rgb_node_r.inputs['Fac'])
					mat.node_tree.links.new(separate_rgb_node1.outputs['G'], mix_rgb_node_g.inputs['Fac'])
					mat.node_tree.links.new(separate_rgb_node1.outputs['B'], mix_rgb_node_b.inputs['Fac'])

					mat.node_tree.links.new(mix_rgb_node_r.outputs['Color'], mix_rgb_node1.inputs['Color1'])
					mat.node_tree.links.new(mix_rgb_node_g.outputs['Color'], mix_rgb_node1.inputs['Color2'])

					mat.node_tree.links.new(mix_rgb_node1.outputs['Color'], mix_rgb_node2.inputs['Color1'])
					mat.node_tree.links.new(mix_rgb_node_b.outputs['Color'], mix_rgb_node2.inputs['Color2'])

					mat.node_tree.links.new(mix_rgb_node2.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Emission'])
					mat.node_tree.nodes[mMaterialId].inputs['Emission Strength'].default_value = mSelfIlluminationMultiplier[0]*10.0

				elif shader_type == "Vehicle_Opaque_Textured_NormalMapped_Emissive_AO_Livery":
					DiffuseTextureSampler_tex = mat.node_tree.nodes['DiffuseTextureSampler']
					NormalTextureSampler_tex = mat.node_tree.nodes['NormalTextureSampler']
					LightmapLightsTextureSampler_tex = mat.node_tree.nodes['LightmapLightsTextureSampler']

					materialDiffuse = parameters_Data[parameters_Names.index("materialDiffuse")]

					mSelfIlluminationMultiplier = parameters_Data[parameters_Names.index("mSelfIlluminationMultiplier")]
					LightmappedLightsRedChannelColour   = parameters_Data[parameters_Names.index("LightmappedLightsRedChannelColour")]
					LightmappedLightsGreenChannelColour = parameters_Data[parameters_Names.index("LightmappedLightsGreenChannelColour")]
					LightmappedLightsBlueChannelColour  = parameters_Data[parameters_Names.index("LightmappedLightsBlueChannelColour")]

					separate_rgb_node1 = mat.node_tree.nodes.new(type='ShaderNodeSeparateRGB')
					mix_rgb_node_r = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					mix_rgb_node_g = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					mix_rgb_node_b = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					mix_rgb_node1 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					mix_rgb_node2 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					mix_rgb_node = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')

					uv_map_node1 = mat.node_tree.nodes.new(type='ShaderNodeUVMap')
					normal_map_node1 = mat.node_tree.nodes.new(type='ShaderNodeNormalMap')

					uv_map_node1.uv_map = "UV3Map"
					normal_map_node1.uv_map = "UV3Map"
					normal_map_node1.inputs['Strength'].default_value = 0.15

					mix_rgb_node.blend_type = "OVERLAY"
					mix_rgb_node.inputs['Color1'].default_value = materialDiffuse

					mix_rgb_node_r.inputs['Color1'].default_value = (0, 0, 0, 0)
					mix_rgb_node_g.inputs['Color1'].default_value = (0, 0, 0, 0)
					mix_rgb_node_b.inputs['Color1'].default_value = (0, 0, 0, 0)

					mix_rgb_node_r.inputs['Color2'].default_value = LightmappedLightsRedChannelColour
					mix_rgb_node_g.inputs['Color2'].default_value = LightmappedLightsGreenChannelColour
					mix_rgb_node_b.inputs['Color2'].default_value = LightmappedLightsBlueChannelColour

					mat.node_tree.links.new(LightmapLightsTextureSampler_tex.outputs['Color'], separate_rgb_node1.inputs['Image'])

					mat.node_tree.links.new(separate_rgb_node1.outputs['R'], mix_rgb_node_r.inputs['Fac'])
					mat.node_tree.links.new(separate_rgb_node1.outputs['G'], mix_rgb_node_g.inputs['Fac'])
					mat.node_tree.links.new(separate_rgb_node1.outputs['B'], mix_rgb_node_b.inputs['Fac'])

					mat.node_tree.links.new(mix_rgb_node_r.outputs['Color'], mix_rgb_node1.inputs['Color1'])
					mat.node_tree.links.new(mix_rgb_node_g.outputs['Color'], mix_rgb_node1.inputs['Color2'])

					mat.node_tree.links.new(mix_rgb_node1.outputs['Color'], mix_rgb_node2.inputs['Color1'])
					mat.node_tree.links.new(mix_rgb_node_b.outputs['Color'], mix_rgb_node2.inputs['Color2'])

					mat.node_tree.links.new(mix_rgb_node2.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Emission'])
					mat.node_tree.nodes[mMaterialId].inputs['Emission Strength'].default_value = mSelfIlluminationMultiplier[0]*10.0

					mat.node_tree.links.new(uv_map_node1.outputs['UV'], DiffuseTextureSampler_tex.inputs['Vector'])
					mat.node_tree.links.new(uv_map_node1.outputs['UV'], NormalTextureSampler_tex.inputs['Vector'])

					mat.node_tree.links.new(NormalTextureSampler_tex.outputs['Color'], normal_map_node1.inputs['Color'])
					mat.node_tree.links.new(normal_map_node1.outputs['Normal'], mat.node_tree.nodes[mMaterialId].inputs['Normal'])

					mat.node_tree.links.new(DiffuseTextureSampler_tex.outputs['Alpha'], mix_rgb_node.inputs['Fac'])
					mat.node_tree.links.new(DiffuseTextureSampler_tex.outputs['Color'], mix_rgb_node.inputs['Color2'])
					mat.node_tree.links.new(mix_rgb_node.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Base Color'])
					mat.node_tree.links.new(DiffuseTextureSampler_tex.outputs['Alpha'], mat.node_tree.nodes[mMaterialId].inputs['Alpha'])

					mat.blend_method = 'OPAQUE'
					mat.shadow_method = 'NONE'

				elif shader_type == "Vehicle_Opaque_Textured_Normalmapped_Reflective_AO":
					DiffuseTextureSampler_tex = mat.node_tree.nodes['DiffuseTextureSampler']

					materialDiffuse = parameters_Data[parameters_Names.index("materialDiffuse")]

					mix_rgb_node = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')

					mix_rgb_node.blend_type = "OVERLAY"

					mix_rgb_node.inputs['Color1'].default_value = materialDiffuse
					mat.node_tree.links.new(DiffuseTextureSampler_tex.outputs['Alpha'], mix_rgb_node.inputs['Fac'])
					mat.node_tree.links.new(DiffuseTextureSampler_tex.outputs['Color'], mix_rgb_node.inputs['Color2'])
					mat.node_tree.links.new(mix_rgb_node.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Base Color'])

					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.5
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 0.25

					mat.blend_method = 'HASHED'
					mat.shadow_method = 'HASHED'

				elif shader_type == "Vehicle_Opaque_Textured_NormalMapped_Reflective_Emissive_AO":
					LightmapLightsTextureSampler_tex = mat.node_tree.nodes['LightmapLightsTextureSampler']

					mSelfIlluminationMultiplier = parameters_Data[parameters_Names.index("mSelfIlluminationMultiplier")]
					LightmappedLightsRedChannelColour   = parameters_Data[parameters_Names.index("LightmappedLightsRedChannelColour")]
					LightmappedLightsGreenChannelColour = parameters_Data[parameters_Names.index("LightmappedLightsGreenChannelColour")]
					LightmappedLightsBlueChannelColour  = parameters_Data[parameters_Names.index("LightmappedLightsBlueChannelColour")]

					separate_rgb_node1 = mat.node_tree.nodes.new(type='ShaderNodeSeparateRGB')
					mix_rgb_node_r = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					mix_rgb_node_g = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					mix_rgb_node_b = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					mix_rgb_node1 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					mix_rgb_node2 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')

					mix_rgb_node_r.inputs['Color1'].default_value = (0, 0, 0, 0)
					mix_rgb_node_g.inputs['Color1'].default_value = (0, 0, 0, 0)
					mix_rgb_node_b.inputs['Color1'].default_value = (0, 0, 0, 0)

					mix_rgb_node_r.inputs['Color2'].default_value = LightmappedLightsRedChannelColour
					mix_rgb_node_g.inputs['Color2'].default_value = LightmappedLightsGreenChannelColour
					mix_rgb_node_b.inputs['Color2'].default_value = LightmappedLightsBlueChannelColour

					mat.node_tree.links.new(LightmapLightsTextureSampler_tex.outputs['Color'], separate_rgb_node1.inputs['Image'])

					mat.node_tree.links.new(separate_rgb_node1.outputs['R'], mix_rgb_node_r.inputs['Fac'])
					mat.node_tree.links.new(separate_rgb_node1.outputs['G'], mix_rgb_node_g.inputs['Fac'])
					mat.node_tree.links.new(separate_rgb_node1.outputs['B'], mix_rgb_node_b.inputs['Fac'])

					mat.node_tree.links.new(mix_rgb_node_r.outputs['Color'], mix_rgb_node1.inputs['Color1'])
					mat.node_tree.links.new(mix_rgb_node_g.outputs['Color'], mix_rgb_node1.inputs['Color2'])

					mat.node_tree.links.new(mix_rgb_node1.outputs['Color'], mix_rgb_node2.inputs['Color1'])
					mat.node_tree.links.new(mix_rgb_node_b.outputs['Color'], mix_rgb_node2.inputs['Color2'])

					mat.node_tree.links.new(mix_rgb_node2.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Emission'])
					mat.node_tree.nodes[mMaterialId].inputs['Emission Strength'].default_value = mSelfIlluminationMultiplier[0]*10.0

					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.5
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 0.25

				elif shader_type == "Vehicle_Opaque_Textured_NormalMapped_Reflective_LocalEmissive_AO":
					EmissiveTextureSampler_tex = mat.node_tree.nodes['EmissiveTextureSampler']

					mSelfIlluminationMultiplier = parameters_Data[parameters_Names.index("mSelfIlluminationMultiplier")]

					mat.node_tree.links.new(EmissiveTextureSampler_tex.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Emission'])
					mat.node_tree.nodes[mMaterialId].inputs['Emission Strength'].default_value = mSelfIlluminationMultiplier[0]*1.0

					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.5
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 0.25

				elif shader_type == "Vehicle_Opaque_Textured_NormalMapped_Reflective_Emissive_AO_Livery":
					DiffuseTextureSampler_tex = mat.node_tree.nodes['DiffuseTextureSampler']
					NormalTextureSampler_tex = mat.node_tree.nodes['NormalTextureSampler']
					LightmapLightsTextureSampler_tex = mat.node_tree.nodes['LightmapLightsTextureSampler']

					mSelfIlluminationMultiplier = parameters_Data[parameters_Names.index("mSelfIlluminationMultiplier")]
					LightmappedLightsRedChannelColour   = parameters_Data[parameters_Names.index("LightmappedLightsRedChannelColour")]
					LightmappedLightsGreenChannelColour = parameters_Data[parameters_Names.index("LightmappedLightsGreenChannelColour")]
					LightmappedLightsBlueChannelColour  = parameters_Data[parameters_Names.index("LightmappedLightsBlueChannelColour")]

					uv_map_node1 = mat.node_tree.nodes.new(type='ShaderNodeUVMap')
					normal_map_node1 = mat.node_tree.nodes.new(type='ShaderNodeNormalMap')

					uv_map_node1.uv_map = "UV3Map"
					normal_map_node1.uv_map = "UV3Map"
					normal_map_node1.inputs['Strength'].default_value = 0.15

					separate_rgb_node1 = mat.node_tree.nodes.new(type='ShaderNodeSeparateRGB')
					mix_rgb_node_r = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					mix_rgb_node_g = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					mix_rgb_node_b = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					mix_rgb_node1 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					mix_rgb_node2 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')

					mix_rgb_node_r.inputs['Color1'].default_value = (0, 0, 0, 0)
					mix_rgb_node_g.inputs['Color1'].default_value = (0, 0, 0, 0)
					mix_rgb_node_b.inputs['Color1'].default_value = (0, 0, 0, 0)

					mix_rgb_node_r.inputs['Color2'].default_value = LightmappedLightsRedChannelColour
					mix_rgb_node_g.inputs['Color2'].default_value = LightmappedLightsGreenChannelColour
					mix_rgb_node_b.inputs['Color2'].default_value = LightmappedLightsBlueChannelColour

					mat.node_tree.links.new(LightmapLightsTextureSampler_tex.outputs['Color'], separate_rgb_node1.inputs['Image'])

					mat.node_tree.links.new(separate_rgb_node1.outputs['R'], mix_rgb_node_r.inputs['Fac'])
					mat.node_tree.links.new(separate_rgb_node1.outputs['G'], mix_rgb_node_g.inputs['Fac'])
					mat.node_tree.links.new(separate_rgb_node1.outputs['B'], mix_rgb_node_b.inputs['Fac'])

					mat.node_tree.links.new(mix_rgb_node_r.outputs['Color'], mix_rgb_node1.inputs['Color1'])
					mat.node_tree.links.new(mix_rgb_node_g.outputs['Color'], mix_rgb_node1.inputs['Color2'])

					mat.node_tree.links.new(mix_rgb_node1.outputs['Color'], mix_rgb_node2.inputs['Color1'])
					mat.node_tree.links.new(mix_rgb_node_b.outputs['Color'], mix_rgb_node2.inputs['Color2'])

					mat.node_tree.links.new(mix_rgb_node2.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Emission'])
					mat.node_tree.nodes[mMaterialId].inputs['Emission Strength'].default_value = mSelfIlluminationMultiplier[0]*1.0

					mat.node_tree.links.new(uv_map_node1.outputs['UV'], DiffuseTextureSampler_tex.inputs['Vector'])
					mat.node_tree.links.new(uv_map_node1.outputs['UV'], NormalTextureSampler_tex.inputs['Vector'])

					#mat.node_tree.links.new(NormalTextureSampler_tex.outputs['Color'], normal_map_node1.inputs['Color'])
					#mat.node_tree.links.new(normal_map_node1.outputs['Normal'], mat.node_tree.nodes[mMaterialId].inputs['Normal'])
					mat.node_tree.links.new(NormalTextureSampler_tex.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Normal'])

					mat.node_tree.links.new(DiffuseTextureSampler_tex.outputs['Alpha'], mat.node_tree.nodes[mMaterialId].inputs['Alpha'])

					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.5
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 0.25

					mat.blend_method = 'HASHED'
					mat.shadow_method = 'HASHED'

				elif shader_type == "Vehicle_Opaque_Textured_Phong":
					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.0
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 1.0

				elif shader_type == "Vehicle_Opaque_Two_PaintGloss_Textured_LightmappedLights_Livery":
					DiffuseTextureSampler_tex = mat.node_tree.nodes['DiffuseTextureSampler']

					uv_map_node1 = mat.node_tree.nodes.new(type='ShaderNodeUVMap')
					mix_rgb_node = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')

					uv_map_node1.uv_map = "UV3Map"
					mix_rgb_node.blend_type = "MIX"

					if random_color == True:
						mix_rgb_node.inputs['Color1'].default_value = RGBA_random
					else:
						mix_rgb_node.inputs['Color1'].default_value = (0.8, 0.8, 0.8, 1.0)

					mat.node_tree.links.new(uv_map_node1.outputs['UV'], DiffuseTextureSampler_tex.inputs['Vector'])
					mat.node_tree.links.new(DiffuseTextureSampler_tex.outputs['Alpha'], mix_rgb_node.inputs['Fac'])
					mat.node_tree.links.new(DiffuseTextureSampler_tex.outputs['Color'], mix_rgb_node.inputs['Color2'])
					mat.node_tree.links.new(mix_rgb_node.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Base Color'])

					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.75
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 0.25

				elif shader_type == "Vehicle_Opaque_Two_PaintGloss_Textured_LightmappedLights_Livery_Wrap":
					DiffuseTextureSampler_tex = mat.node_tree.nodes['DiffuseTextureSampler']

					uv_map_node1 = mat.node_tree.nodes.new(type='ShaderNodeUVMap')
					mix_rgb_node = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')

					uv_map_node1.uv_map = "UV3Map"
					mix_rgb_node.blend_type = "MIX"

					if random_color == True:
						mix_rgb_node.inputs['Color1'].default_value = RGBA_random
					else:
						mix_rgb_node.inputs['Color1'].default_value = (0.8, 0.8, 0.8, 1.0)

					mat.node_tree.links.new(uv_map_node1.outputs['UV'], DiffuseTextureSampler_tex.inputs['Vector'])
					mat.node_tree.links.new(DiffuseTextureSampler_tex.outputs['Alpha'], mix_rgb_node.inputs['Fac'])
					mat.node_tree.links.new(DiffuseTextureSampler_tex.outputs['Color'], mix_rgb_node.inputs['Color2'])
					mat.node_tree.links.new(mix_rgb_node.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Base Color'])

					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.75
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 0.25

				elif shader_type == "Vehicle_Rearlights_Heightmap":
					DiffuseSampler_tex = mat.node_tree.nodes['DiffuseSampler']
					EmissiveTextureSampler_tex = mat.node_tree.nodes['EmissiveTextureSampler']
					InternalNormalTextureSampler_tex = mat.node_tree.nodes['InternalNormalTextureSampler']
					ExternalNormalTextureSampler_tex = mat.node_tree.nodes['ExternalNormalTextureSampler']

					mSelfIlluminationBrightness = parameters_Data[parameters_Names.index("mSelfIlluminationBrightness")]
					BrakeColour   = parameters_Data[parameters_Names.index("BrakeColour")]
					RunningColour = parameters_Data[parameters_Names.index("RunningColour")]
					ReversingColour  = parameters_Data[parameters_Names.index("ReversingColour")]
					#TaillightColour = parameters_Data[parameters_Names.index("TaillightColour")]

					separate_rgb_node1 = mat.node_tree.nodes.new(type='ShaderNodeSeparateRGB')
					mix_rgb_node_r = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					mix_rgb_node_g = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					mix_rgb_node_b = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					mix_rgb_node1 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					mix_rgb_node2 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					normal_map_node1 = mat.node_tree.nodes.new(type='ShaderNodeNormalMap')
					normal_map_node2 = mat.node_tree.nodes.new(type='ShaderNodeNormalMap')
					vector_math_node1 = mat.node_tree.nodes.new(type='ShaderNodeVectorMath')

					normal_map_node1.uv_map = "UVMap"
					normal_map_node2.uv_map = "UVMap"
					vector_math_node1.operation = "REFRACT"
					vector_math_node1.inputs[3].default_value = 1.1

					mix_rgb_node_r.inputs['Color1'].default_value = (0, 0, 0, 0)
					mix_rgb_node_g.inputs['Color1'].default_value = (0, 0, 0, 0)
					mix_rgb_node_b.inputs['Color1'].default_value = (0, 0, 0, 0)

					mix_rgb_node_r.inputs['Color2'].default_value = BrakeColour
					mix_rgb_node_g.inputs['Color2'].default_value = RunningColour
					mix_rgb_node_b.inputs['Color2'].default_value = ReversingColour

					mat.node_tree.links.new(EmissiveTextureSampler_tex.outputs['Color'], separate_rgb_node1.inputs['Image'])

					mat.node_tree.links.new(separate_rgb_node1.outputs['R'], mix_rgb_node_r.inputs['Fac'])
					mat.node_tree.links.new(separate_rgb_node1.outputs['G'], mix_rgb_node_g.inputs['Fac'])
					mat.node_tree.links.new(separate_rgb_node1.outputs['B'], mix_rgb_node_b.inputs['Fac'])

					mat.node_tree.links.new(mix_rgb_node_r.outputs['Color'], mix_rgb_node1.inputs['Color1'])
					mat.node_tree.links.new(mix_rgb_node_g.outputs['Color'], mix_rgb_node1.inputs['Color2'])

					mat.node_tree.links.new(mix_rgb_node1.outputs['Color'], mix_rgb_node2.inputs['Color1'])
					mat.node_tree.links.new(mix_rgb_node_b.outputs['Color'], mix_rgb_node2.inputs['Color2'])

					mat.node_tree.links.new(mix_rgb_node2.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Emission'])
					mat.node_tree.nodes[mMaterialId].inputs['Emission Strength'].default_value = mSelfIlluminationBrightness[0]*10.0

					mat.node_tree.links.new(InternalNormalTextureSampler_tex.outputs['Color'], normal_map_node1.inputs['Color'])
					mat.node_tree.links.new(ExternalNormalTextureSampler_tex.outputs['Color'], normal_map_node2.inputs['Color'])

					mat.node_tree.links.new(normal_map_node1.outputs['Normal'], vector_math_node1.inputs[0])
					mat.node_tree.links.new(normal_map_node2.outputs['Normal'], vector_math_node1.inputs[1])

					mat.node_tree.links.new(vector_math_node1.outputs['Vector'], mat.node_tree.nodes[mMaterialId].inputs['Normal'])

					mat.node_tree.links.new(DiffuseSampler_tex.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Base Color'])

					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.2
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 0.3

				elif shader_type == "Vehicle_Wheel_1Bit_Alpha":
					DiffuseTextureSampler_tex = mat.node_tree.nodes['DiffuseTextureSampler']

					mat.node_tree.links.new(DiffuseTextureSampler_tex.outputs['Alpha'], mat.node_tree.nodes[mMaterialId].inputs['Alpha'])

					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.5
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 0.4

					mat.blend_method = 'HASHED'
					mat.shadow_method = 'HASHED'

				elif shader_type == "Vehicle_Wheel_1Bit_Alpha_Normalmap":
					DiffuseTextureSampler_tex = mat.node_tree.nodes['DiffuseTextureSampler']

					mMaterialDiffuse = parameters_Data[parameters_Names.index("mMaterialDiffuse")]

					mix_rgb_node = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')

					mix_rgb_node.blend_type = "OVERLAY"

					mix_rgb_node.inputs['Color1'].default_value = mMaterialDiffuse
					mat.node_tree.links.new(DiffuseTextureSampler_tex.outputs['Alpha'], mix_rgb_node.inputs['Fac'])
					mat.node_tree.links.new(DiffuseTextureSampler_tex.outputs['Color'], mix_rgb_node.inputs['Color2'])
					mat.node_tree.links.new(mix_rgb_node.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Base Color'])

					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.5
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 0.5

					mat.blend_method = 'HASHED'
					mat.shadow_method = 'HASHED'

				elif shader_type == "Vehicle_Wheel_Alpha_Normalmap":
					DiffuseTextureSampler_tex = mat.node_tree.nodes['DiffuseTextureSampler']

					mat.node_tree.links.new(DiffuseTextureSampler_tex.outputs['Alpha'], mat.node_tree.nodes[mMaterialId].inputs['Alpha'])

					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.8
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 0.2

					mat.blend_method = 'HASHED'
					mat.shadow_method = 'HASHED'

				elif shader_type == "Vehicle_Wheel_Alpha_Blur_Normalmap":
					DiffuseTextureSampler_tex = mat.node_tree.nodes['DiffuseTextureSampler']

					mat.node_tree.links.new(DiffuseTextureSampler_tex.outputs['Alpha'], mat.node_tree.nodes[mMaterialId].inputs['Alpha'])

					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.8
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 0.2

					mat.blend_method = 'HASHED'
					mat.shadow_method = 'HASHED'

				elif shader_type == "Vehicle_Wheel_Brakedisc_1Bit_Blur_Normalmap":
					DiffuseTextureSampler_tex = mat.node_tree.nodes['DiffuseTextureSampler']
					NormalTextureSampler_tex = mat.node_tree.nodes['NormalTextureSampler']
					SpecularAndAOTextureSampler_tex = mat.node_tree.nodes['SpecularAndAOTextureSampler']

					mat.node_tree.links.new(SpecularAndAOTextureSampler_tex.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Specular'])
					mat.node_tree.links.new(DiffuseTextureSampler_tex.outputs['Alpha'], mat.node_tree.nodes[mMaterialId].inputs['Alpha'])

					mat.node_tree.links.new(NormalTextureSampler_tex.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Normal'])

					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.0
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 1.0

					mat.blend_method = 'HASHED'
					mat.shadow_method = 'HASHED'

				elif shader_type == "Vehicle_Wheel_Opaque":
					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.8
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 0.2

				elif shader_type == "Vehicle_Tyre":
					NormalTextureSampler_tex = mat.node_tree.nodes['NormalTextureSampler']
					mSpecularControls = parameters_Data[parameters_Names.index("mSpecularControls")]

					normal_map_node1 = mat.node_tree.nodes.new(type='ShaderNodeNormalMap')

					normal_map_node1.uv_map = "UVMap"
					normal_map_node1.inputs['Strength'].default_value = 0.4

					mat.node_tree.links.new(NormalTextureSampler_tex.outputs['Color'], normal_map_node1.inputs['Color'])
					mat.node_tree.links.new(normal_map_node1.outputs['Normal'], mat.node_tree.nodes[mMaterialId].inputs['Normal'])

					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.0
					mat.node_tree.nodes[mMaterialId].inputs['Specular'].default_value = mSpecularControls[0]
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 1.0

				elif "Vehicle" in shader_type:
					print("DEBUG: shader type %s, used on material %s, still does not have its shading set." % (shader_type, mMaterialId))

				# Character
				elif shader_type == "Character_Greyscale_Textured_Doublesided_Skin":
					DiffuseTextureSampler_tex = mat.node_tree.nodes['DiffuseTextureSampler']

					mat.node_tree.links.new(DiffuseTextureSampler_tex.outputs['Alpha'], mat.node_tree.nodes[mMaterialId].inputs['Alpha'])

					mat.blend_method = 'BLEND'
					mat.shadow_method = 'HASHED'

					mat.node_tree.nodes[mMaterialId].inputs['Specular'].default_value = 0.0

				elif shader_type == "Character_Opaque_Textured_NormalMap_SpecMap_Skin":
					#Removing normal link
					if len(mat.node_tree.nodes[mMaterialId].inputs['Normal'].links) > 0:
						link = mat.node_tree.nodes[mMaterialId].inputs['Normal'].links[0]
						mat.node_tree.links.remove(link)

					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.2
					mat.node_tree.nodes[mMaterialId].inputs['Specular'].default_value = 0.1
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 0.4

				# World
				elif shader_type == "Armco_Opaque_Doublesided":
					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.4
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 0.6

					mat.use_backface_culling = False

				elif shader_type == "Bush_Translucent_1Bit_Doublesided":
					DiffuseTextureSampler_tex = mat.node_tree.nodes['DiffuseTextureSampler']

					mat.node_tree.links.new(DiffuseTextureSampler_tex.outputs['Alpha'], mat.node_tree.nodes[mMaterialId].inputs['Alpha'])

					mat.blend_method = 'BLEND'
					mat.shadow_method = 'HASHED'

					mat.use_backface_culling = False

					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.2
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 0.8

				elif shader_type == "Bush_Translucent_1Bit_Normal_Spec_Doublesided":
					DiffuseTextureSampler_tex = mat.node_tree.nodes['DiffuseTextureSampler']

					mat.node_tree.links.new(DiffuseTextureSampler_tex.outputs['Alpha'], mat.node_tree.nodes[mMaterialId].inputs['Alpha'])

					mat.blend_method = 'BLEND'
					mat.shadow_method = 'HASHED'

					mat.use_backface_culling = False

					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.2
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 0.8

				elif shader_type == "CatsEyes":
					DiffuseSampler_tex = mat.node_tree.nodes['DiffuseSampler']

					SizeX_SizeY_DepthBias_Brightness = parameters_Data[parameters_Names.index("SizeX_SizeY_DepthBias_Brightness")]

					mat.node_tree.links.new(DiffuseSampler_tex.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Base Color'])
					mat.node_tree.links.new(DiffuseSampler_tex.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Emission'])
					mat.node_tree.links.new(DiffuseSampler_tex.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Alpha'])
					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 1.0
					mat.node_tree.nodes[mMaterialId].inputs['Specular'].default_value = 0.0
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 0.0
					mat.node_tree.nodes[mMaterialId].inputs['Emission Strength'].default_value = SizeX_SizeY_DepthBias_Brightness[3]*10.0

				elif shader_type == "CatsEyesGeometry":
					DiffuseTextureSampler_tex = mat.node_tree.nodes['DiffuseTextureSampler']

					RetroreflectiveThreshold = parameters_Data[parameters_Names.index("RetroreflectiveThreshold")]

					mat.node_tree.links.new(DiffuseTextureSampler_tex.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Emission'])
					mat.node_tree.nodes[mMaterialId].inputs['Emission Strength'].default_value = RetroreflectiveThreshold[0]*1.0

				elif shader_type == "DEBUG_TRIGGER_Illuminance_Greyscale_Singlesided":
					IlluminanceTextureSampler_tex = mat.node_tree.nodes['IlluminanceTextureSampler']

					#mat.node_tree.links.new(IlluminanceTextureSampler_tex.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Emission'])
					mat.node_tree.nodes[mMaterialId].inputs['Emission'].default_value = (1.0, 0.0, 0.0, 1.0)
					mat.node_tree.nodes[mMaterialId].inputs['Emission Strength'].default_value = 1.0

					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.3
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 0.5

					mat.use_backface_culling = True

				elif shader_type == "Deflicker_World_Diffuse_Normal_Specular_Singlesided":
					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.1
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 1.0

					mat.use_backface_culling = True

				elif shader_type == "Deflicker_World_Diffuse_Normal_Specular_Overlay_Singlesided":
					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.1
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 0.8

					mat.use_backface_culling = True

				elif shader_type == "Deflicker_World_Diffuse_Specular_Singlesided":
					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.1
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 0.8

					mat.use_backface_culling = True

				elif shader_type == "Deflicker_World_Diffuse_Specular_Overlay_Singlesided":
					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.1
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 0.8

					mat.use_backface_culling = True

				elif shader_type == "Deflicker_World_Diffuse_Specular_Overlay_IlluminanceNight_Singlesided":
					IlluminanceTextureSampler_tex = mat.node_tree.nodes['IlluminanceTextureSampler']

					mat.node_tree.links.new(IlluminanceTextureSampler_tex.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Emission'])

					mat.node_tree.nodes[mMaterialId].inputs['Emission Strength'].default_value = 0.6

					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.3
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 0.5

					mat.use_backface_culling = True

				elif shader_type == "DICETerrain3Cheap_Proto":
					Tiling1TextureSampler_tex = mat.node_tree.nodes['Tiling1TextureSampler']
					Tiling2TextureSampler_tex = mat.node_tree.nodes['Tiling2TextureSampler']
					Tiling3TextureSampler_tex = mat.node_tree.nodes['Tiling3TextureSampler']
					MaskTextureSampler_tex = mat.node_tree.nodes['MaskTextureSampler']
					NoiseTextureSampler_tex = mat.node_tree.nodes['NoiseTextureSampler']
					Tiling1NormalSampler_tex = mat.node_tree.nodes['Tiling1NormalSampler']
					Tiling2NormalSampler_tex = mat.node_tree.nodes['Tiling2NormalSampler']
					Tiling3NormalSampler_tex = mat.node_tree.nodes['Tiling3NormalSampler']

					mix_rgb_node1 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					mix_rgb_node2 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					separate_rgb_node1 = mat.node_tree.nodes.new(type='ShaderNodeSeparateRGB')
					uv_map_node1 = mat.node_tree.nodes.new(type='ShaderNodeUVMap')
					mapping_node1 = mat.node_tree.nodes.new(type='ShaderNodeMapping')
					mapping_node2 = mat.node_tree.nodes.new(type='ShaderNodeMapping')
					mapping_node3 = mat.node_tree.nodes.new(type='ShaderNodeMapping')
					mapping_node4 = mat.node_tree.nodes.new(type='ShaderNodeMapping')

					uv_map_node1.uv_map = "UV2Map"

					Tiling_Ratios_X = parameters_Data[parameters_Names.index("Tiling_Ratios_X")]
					Tiling_Ratios_Y = parameters_Data[parameters_Names.index("Tiling_Ratios_Y")]
					Tiling_Ratio_Noise = parameters_Data[parameters_Names.index("Tiling_Ratio_Noise")]

					mat.node_tree.links.new(uv_map_node1.outputs['UV'], mapping_node1.inputs[0])
					mat.node_tree.links.new(uv_map_node1.outputs['UV'], mapping_node2.inputs[0])
					mat.node_tree.links.new(uv_map_node1.outputs['UV'], mapping_node3.inputs[0])
					mat.node_tree.links.new(uv_map_node1.outputs['UV'], mapping_node4.inputs[0])

					mapping_node1.inputs[3].default_value[0] = Tiling_Ratios_X[0]*1.0
					mapping_node1.inputs[3].default_value[1] = Tiling_Ratios_Y[0]*1.0

					mapping_node2.inputs[3].default_value[0] = Tiling_Ratios_X[1]*1.0
					mapping_node2.inputs[3].default_value[1] = Tiling_Ratios_Y[1]*1.0

					mapping_node3.inputs[3].default_value[0] = Tiling_Ratios_X[2]*1.0
					mapping_node3.inputs[3].default_value[1] = Tiling_Ratios_Y[2]*1.0

					mapping_node4.inputs[3].default_value[0] = Tiling_Ratio_Noise[0]*1.0
					mapping_node4.inputs[3].default_value[1] = Tiling_Ratio_Noise[0]*1.0

					mat.node_tree.links.new(mapping_node1.outputs['Vector'], Tiling1TextureSampler_tex.inputs['Vector'])
					mat.node_tree.links.new(mapping_node2.outputs['Vector'], Tiling2TextureSampler_tex.inputs['Vector'])
					mat.node_tree.links.new(mapping_node3.outputs['Vector'], Tiling3TextureSampler_tex.inputs['Vector'])
					mat.node_tree.links.new(mapping_node4.outputs['Vector'], NoiseTextureSampler_tex.inputs['Vector'])

					mat.node_tree.links.new(MaskTextureSampler_tex.outputs['Color'], separate_rgb_node1.inputs['Image'])

					mat.node_tree.links.new(separate_rgb_node1.outputs['B'], mix_rgb_node1.inputs['Fac'])
					mat.node_tree.links.new(Tiling1TextureSampler_tex.outputs['Color'], mix_rgb_node1.inputs['Color1'])
					mat.node_tree.links.new(Tiling3TextureSampler_tex.outputs['Color'], mix_rgb_node1.inputs['Color2'])

					mat.node_tree.links.new(separate_rgb_node1.outputs['R'], mix_rgb_node2.inputs['Fac'])
					mat.node_tree.links.new(Tiling2TextureSampler_tex.outputs['Color'], mix_rgb_node2.inputs['Color1'])
					mat.node_tree.links.new(mix_rgb_node1.outputs['Color'], mix_rgb_node2.inputs['Color2'])

					mat.node_tree.links.new(mix_rgb_node2.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Base Color'])

					#Normal
					mix_rgb_node11 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					mix_rgb_node12 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')

					mat.node_tree.links.new(mapping_node1.outputs['Vector'], Tiling1NormalSampler_tex.inputs['Vector'])
					mat.node_tree.links.new(mapping_node2.outputs['Vector'], Tiling2NormalSampler_tex.inputs['Vector'])
					mat.node_tree.links.new(mapping_node3.outputs['Vector'], Tiling3NormalSampler_tex.inputs['Vector'])

					mat.node_tree.links.new(separate_rgb_node1.outputs['B'], mix_rgb_node11.inputs['Fac'])
					mat.node_tree.links.new(Tiling1NormalSampler_tex.outputs['Color'], mix_rgb_node11.inputs['Color1'])
					mat.node_tree.links.new(Tiling3NormalSampler_tex.outputs['Color'], mix_rgb_node11.inputs['Color2'])

					mat.node_tree.links.new(separate_rgb_node1.outputs['R'], mix_rgb_node12.inputs['Fac'])
					mat.node_tree.links.new(Tiling2NormalSampler_tex.outputs['Color'], mix_rgb_node12.inputs['Color1'])
					mat.node_tree.links.new(mix_rgb_node11.outputs['Color'], mix_rgb_node12.inputs['Color2'])

					mat.node_tree.links.new(mix_rgb_node12.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Normal'])

					#Shading
					mat.node_tree.nodes[mMaterialId].inputs['Specular'].default_value = 0.1
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 0.8

				elif shader_type == "DICETerrain3_Proto":
					Tiling1TextureSampler_tex = mat.node_tree.nodes['Tiling1TextureSampler']
					Tiling2TextureSampler_tex = mat.node_tree.nodes['Tiling2TextureSampler']
					Tiling3TextureSampler_tex = mat.node_tree.nodes['Tiling3TextureSampler']
					CliffTextureSampler_tex = mat.node_tree.nodes['CliffTextureSampler']
					MaskTextureSampler_tex = mat.node_tree.nodes['MaskTextureSampler']
					CliffMaskAndLightingTextureSampler_tex = mat.node_tree.nodes['CliffMaskAndLightingTextureSampler']
					NoiseTextureSampler_tex = mat.node_tree.nodes['NoiseTextureSampler']
					NormalTextureSampler_tex = mat.node_tree.nodes['NormalTextureSampler']
					Tiling1NormalSampler_tex = mat.node_tree.nodes['Tiling1NormalSampler']
					Tiling2NormalSampler_tex = mat.node_tree.nodes['Tiling2NormalSampler']
					Tiling3NormalSampler_tex = mat.node_tree.nodes['Tiling3NormalSampler']
					CliffNormalSampler_tex = mat.node_tree.nodes['CliffNormalSampler']
					RGBOverlayTextureSampler_tex = mat.node_tree.nodes['RGBOverlayTextureSampler']

					mix_rgb_node1 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					mix_rgb_node2 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					mix_rgb_node3 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					separate_rgb_node1 = mat.node_tree.nodes.new(type='ShaderNodeSeparateRGB')
					uv_map_node1 = mat.node_tree.nodes.new(type='ShaderNodeUVMap')
					uv_map_node2 = mat.node_tree.nodes.new(type='ShaderNodeUVMap')
					mapping_node1 = mat.node_tree.nodes.new(type='ShaderNodeMapping')
					mapping_node2 = mat.node_tree.nodes.new(type='ShaderNodeMapping')
					mapping_node3 = mat.node_tree.nodes.new(type='ShaderNodeMapping')
					mapping_node4 = mat.node_tree.nodes.new(type='ShaderNodeMapping')
					mapping_node5 = mat.node_tree.nodes.new(type='ShaderNodeMapping')

					uv_map_node1.uv_map = "UV2Map"
					uv_map_node2.uv_map = "UV3Map"

					Tiling_Ratios_X = parameters_Data[parameters_Names.index("Tiling_Ratios_X")]
					Tiling_Ratios_Y = parameters_Data[parameters_Names.index("Tiling_Ratios_Y")]
					Tiling_Ratio_Noise = parameters_Data[parameters_Names.index("Tiling_Ratio_Noise")]
					Tiling_Ratios_Cliffs = parameters_Data[parameters_Names.index("Tiling_Ratios_Cliffs")]

					mat.node_tree.links.new(uv_map_node1.outputs['UV'], mapping_node1.inputs[0])
					mat.node_tree.links.new(uv_map_node1.outputs['UV'], mapping_node2.inputs[0])
					mat.node_tree.links.new(uv_map_node1.outputs['UV'], mapping_node3.inputs[0])
					mat.node_tree.links.new(uv_map_node1.outputs['UV'], mapping_node4.inputs[0])
					mat.node_tree.links.new(uv_map_node2.outputs['UV'], mapping_node5.inputs[0])

					mapping_node1.inputs[3].default_value[0] = Tiling_Ratios_X[0]*1.0
					mapping_node1.inputs[3].default_value[1] = Tiling_Ratios_Y[0]*1.0

					mapping_node2.inputs[3].default_value[0] = Tiling_Ratios_X[1]*1.0
					mapping_node2.inputs[3].default_value[1] = Tiling_Ratios_Y[1]*1.0

					mapping_node3.inputs[3].default_value[0] = Tiling_Ratios_X[2]*1.0
					mapping_node3.inputs[3].default_value[1] = Tiling_Ratios_Y[2]*1.0

					mapping_node4.inputs[3].default_value[0] = Tiling_Ratio_Noise[0]*1.0
					mapping_node4.inputs[3].default_value[1] = Tiling_Ratio_Noise[0]*1.0

					mapping_node5.inputs[3].default_value[0] = Tiling_Ratios_Cliffs[0]*1.0
					mapping_node5.inputs[3].default_value[1] = Tiling_Ratios_Cliffs[1]*1.0

					mat.node_tree.links.new(mapping_node1.outputs['Vector'], Tiling1TextureSampler_tex.inputs['Vector'])
					mat.node_tree.links.new(mapping_node2.outputs['Vector'], Tiling2TextureSampler_tex.inputs['Vector'])
					mat.node_tree.links.new(mapping_node3.outputs['Vector'], Tiling3TextureSampler_tex.inputs['Vector'])
					mat.node_tree.links.new(mapping_node4.outputs['Vector'], NoiseTextureSampler_tex.inputs['Vector'])
					mat.node_tree.links.new(mapping_node5.outputs['Vector'], CliffTextureSampler_tex.inputs['Vector'])

					mat.node_tree.links.new(MaskTextureSampler_tex.outputs['Color'], separate_rgb_node1.inputs['Image'])

					mat.node_tree.links.new(separate_rgb_node1.outputs['B'], mix_rgb_node1.inputs['Fac'])
					mat.node_tree.links.new(Tiling1TextureSampler_tex.outputs['Color'], mix_rgb_node1.inputs['Color1'])
					mat.node_tree.links.new(Tiling3TextureSampler_tex.outputs['Color'], mix_rgb_node1.inputs['Color2'])

					mat.node_tree.links.new(separate_rgb_node1.outputs['R'], mix_rgb_node2.inputs['Fac'])
					mat.node_tree.links.new(Tiling2TextureSampler_tex.outputs['Color'], mix_rgb_node2.inputs['Color1'])
					mat.node_tree.links.new(mix_rgb_node1.outputs['Color'], mix_rgb_node2.inputs['Color2'])

					mat.node_tree.links.new(CliffMaskAndLightingTextureSampler_tex.outputs['Color'], mix_rgb_node3.inputs['Fac'])
					mat.node_tree.links.new(mix_rgb_node2.outputs['Color'], mix_rgb_node3.inputs['Color1'])
					mat.node_tree.links.new(CliffTextureSampler_tex.outputs['Color'], mix_rgb_node3.inputs['Color2'])

					mat.node_tree.links.new(mix_rgb_node3.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Base Color'])

					#Normal
					mix_rgb_node11 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					mix_rgb_node12 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					mix_rgb_node13 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')

					mat.node_tree.links.new(mapping_node1.outputs['Vector'], Tiling1NormalSampler_tex.inputs['Vector'])
					mat.node_tree.links.new(mapping_node2.outputs['Vector'], Tiling2NormalSampler_tex.inputs['Vector'])
					mat.node_tree.links.new(mapping_node3.outputs['Vector'], Tiling3NormalSampler_tex.inputs['Vector'])
					mat.node_tree.links.new(mapping_node5.outputs['Vector'], CliffNormalSampler_tex.inputs['Vector'])

					mat.node_tree.links.new(separate_rgb_node1.outputs['B'], mix_rgb_node11.inputs['Fac'])
					mat.node_tree.links.new(Tiling1NormalSampler_tex.outputs['Color'], mix_rgb_node11.inputs['Color1'])
					mat.node_tree.links.new(Tiling3NormalSampler_tex.outputs['Color'], mix_rgb_node11.inputs['Color2'])

					mat.node_tree.links.new(separate_rgb_node1.outputs['R'], mix_rgb_node12.inputs['Fac'])
					mat.node_tree.links.new(Tiling2NormalSampler_tex.outputs['Color'], mix_rgb_node12.inputs['Color1'])
					mat.node_tree.links.new(mix_rgb_node11.outputs['Color'], mix_rgb_node12.inputs['Color2'])

					mat.node_tree.links.new(CliffMaskAndLightingTextureSampler_tex.outputs['Color'], mix_rgb_node13.inputs['Fac'])
					mat.node_tree.links.new(mix_rgb_node12.outputs['Color'], mix_rgb_node13.inputs['Color1'])
					mat.node_tree.links.new(CliffNormalSampler_tex.outputs['Color'], mix_rgb_node13.inputs['Color2'])

					mat.node_tree.links.new(mix_rgb_node13.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Normal'])

					#Shading
					mat.node_tree.nodes[mMaterialId].inputs['Specular'].default_value = 0.1
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 0.8

				elif shader_type == "DICETerrain3NoRGB_Proto":
					Tiling1TextureSampler_tex = mat.node_tree.nodes['Tiling1TextureSampler']
					Tiling2TextureSampler_tex = mat.node_tree.nodes['Tiling2TextureSampler']
					Tiling3TextureSampler_tex = mat.node_tree.nodes['Tiling3TextureSampler']
					CliffTextureSampler_tex = mat.node_tree.nodes['CliffTextureSampler']
					MaskTextureSampler_tex = mat.node_tree.nodes['MaskTextureSampler']
					CliffMaskAndLightingTextureSampler_tex = mat.node_tree.nodes['CliffMaskAndLightingTextureSampler']
					NoiseTextureSampler_tex = mat.node_tree.nodes['NoiseTextureSampler']
					NormalTextureSampler_tex = mat.node_tree.nodes['NormalTextureSampler']
					Tiling1NormalSampler_tex = mat.node_tree.nodes['Tiling1NormalSampler']
					Tiling2NormalSampler_tex = mat.node_tree.nodes['Tiling2NormalSampler']
					Tiling3NormalSampler_tex = mat.node_tree.nodes['Tiling3NormalSampler']
					CliffNormalSampler_tex = mat.node_tree.nodes['CliffNormalSampler']

					mix_rgb_node1 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					mix_rgb_node2 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					mix_rgb_node3 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					separate_rgb_node1 = mat.node_tree.nodes.new(type='ShaderNodeSeparateRGB')
					uv_map_node1 = mat.node_tree.nodes.new(type='ShaderNodeUVMap')
					uv_map_node2 = mat.node_tree.nodes.new(type='ShaderNodeUVMap')
					mapping_node1 = mat.node_tree.nodes.new(type='ShaderNodeMapping')
					mapping_node2 = mat.node_tree.nodes.new(type='ShaderNodeMapping')
					mapping_node3 = mat.node_tree.nodes.new(type='ShaderNodeMapping')
					mapping_node4 = mat.node_tree.nodes.new(type='ShaderNodeMapping')
					mapping_node5 = mat.node_tree.nodes.new(type='ShaderNodeMapping')

					uv_map_node1.uv_map = "UV2Map"
					uv_map_node2.uv_map = "UV3Map"

					Tiling_Ratios_X = parameters_Data[parameters_Names.index("Tiling_Ratios_X")]
					Tiling_Ratios_Y = parameters_Data[parameters_Names.index("Tiling_Ratios_Y")]
					Tiling_Ratio_Noise = parameters_Data[parameters_Names.index("Tiling_Ratio_Noise")]
					Tiling_Ratios_Cliffs = parameters_Data[parameters_Names.index("Tiling_Ratios_Cliffs")]

					mat.node_tree.links.new(uv_map_node1.outputs['UV'], mapping_node1.inputs[0])
					mat.node_tree.links.new(uv_map_node1.outputs['UV'], mapping_node2.inputs[0])
					mat.node_tree.links.new(uv_map_node1.outputs['UV'], mapping_node3.inputs[0])
					mat.node_tree.links.new(uv_map_node1.outputs['UV'], mapping_node4.inputs[0])
					mat.node_tree.links.new(uv_map_node2.outputs['UV'], mapping_node5.inputs[0])

					mapping_node1.inputs[3].default_value[0] = Tiling_Ratios_X[0]*1.0
					mapping_node1.inputs[3].default_value[1] = Tiling_Ratios_Y[0]*1.0

					mapping_node2.inputs[3].default_value[0] = Tiling_Ratios_X[1]*1.0
					mapping_node2.inputs[3].default_value[1] = Tiling_Ratios_Y[1]*1.0

					mapping_node3.inputs[3].default_value[0] = Tiling_Ratios_X[2]*1.0
					mapping_node3.inputs[3].default_value[1] = Tiling_Ratios_Y[2]*1.0

					mapping_node4.inputs[3].default_value[0] = Tiling_Ratio_Noise[0]*1.0
					mapping_node4.inputs[3].default_value[1] = Tiling_Ratio_Noise[0]*1.0

					mapping_node5.inputs[3].default_value[0] = Tiling_Ratios_Cliffs[0]*1.0
					mapping_node5.inputs[3].default_value[1] = Tiling_Ratios_Cliffs[1]*1.0

					mat.node_tree.links.new(mapping_node1.outputs['Vector'], Tiling1TextureSampler_tex.inputs['Vector'])
					mat.node_tree.links.new(mapping_node2.outputs['Vector'], Tiling2TextureSampler_tex.inputs['Vector'])
					mat.node_tree.links.new(mapping_node3.outputs['Vector'], Tiling3TextureSampler_tex.inputs['Vector'])
					mat.node_tree.links.new(mapping_node4.outputs['Vector'], NoiseTextureSampler_tex.inputs['Vector'])
					mat.node_tree.links.new(mapping_node5.outputs['Vector'], CliffTextureSampler_tex.inputs['Vector'])

					mat.node_tree.links.new(MaskTextureSampler_tex.outputs['Color'], separate_rgb_node1.inputs['Image'])

					mat.node_tree.links.new(separate_rgb_node1.outputs['B'], mix_rgb_node1.inputs['Fac'])
					mat.node_tree.links.new(Tiling1TextureSampler_tex.outputs['Color'], mix_rgb_node1.inputs['Color1'])
					mat.node_tree.links.new(Tiling3TextureSampler_tex.outputs['Color'], mix_rgb_node1.inputs['Color2'])

					mat.node_tree.links.new(separate_rgb_node1.outputs['R'], mix_rgb_node2.inputs['Fac'])
					mat.node_tree.links.new(Tiling2TextureSampler_tex.outputs['Color'], mix_rgb_node2.inputs['Color1'])
					mat.node_tree.links.new(mix_rgb_node1.outputs['Color'], mix_rgb_node2.inputs['Color2'])

					mat.node_tree.links.new(CliffMaskAndLightingTextureSampler_tex.outputs['Color'], mix_rgb_node3.inputs['Fac'])
					mat.node_tree.links.new(mix_rgb_node2.outputs['Color'], mix_rgb_node3.inputs['Color1'])
					mat.node_tree.links.new(CliffTextureSampler_tex.outputs['Color'], mix_rgb_node3.inputs['Color2'])

					mat.node_tree.links.new(mix_rgb_node3.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Base Color'])

					#Normal
					mix_rgb_node11 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					mix_rgb_node12 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					mix_rgb_node13 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')

					mat.node_tree.links.new(mapping_node1.outputs['Vector'], Tiling1NormalSampler_tex.inputs['Vector'])
					mat.node_tree.links.new(mapping_node2.outputs['Vector'], Tiling2NormalSampler_tex.inputs['Vector'])
					mat.node_tree.links.new(mapping_node3.outputs['Vector'], Tiling3NormalSampler_tex.inputs['Vector'])
					mat.node_tree.links.new(mapping_node5.outputs['Vector'], CliffNormalSampler_tex.inputs['Vector'])

					mat.node_tree.links.new(separate_rgb_node1.outputs['B'], mix_rgb_node11.inputs['Fac'])
					mat.node_tree.links.new(Tiling1NormalSampler_tex.outputs['Color'], mix_rgb_node11.inputs['Color1'])
					mat.node_tree.links.new(Tiling3NormalSampler_tex.outputs['Color'], mix_rgb_node11.inputs['Color2'])

					mat.node_tree.links.new(separate_rgb_node1.outputs['R'], mix_rgb_node12.inputs['Fac'])
					mat.node_tree.links.new(Tiling2NormalSampler_tex.outputs['Color'], mix_rgb_node12.inputs['Color1'])
					mat.node_tree.links.new(mix_rgb_node11.outputs['Color'], mix_rgb_node12.inputs['Color2'])

					mat.node_tree.links.new(CliffMaskAndLightingTextureSampler_tex.outputs['Color'], mix_rgb_node13.inputs['Fac'])
					mat.node_tree.links.new(mix_rgb_node12.outputs['Color'], mix_rgb_node13.inputs['Color1'])
					mat.node_tree.links.new(CliffNormalSampler_tex.outputs['Color'], mix_rgb_node13.inputs['Color2'])

					mat.node_tree.links.new(mix_rgb_node13.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Normal'])

					#Shading
					mat.node_tree.nodes[mMaterialId].inputs['Specular'].default_value = 0.1
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 0.8

				elif shader_type == "DICETerrain3CliffsOnly_Proto":
					CliffTextureSampler_tex = mat.node_tree.nodes['CliffTextureSampler']
					MaskTextureSampler_tex = mat.node_tree.nodes['MaskTextureSampler']
					NormalTextureSampler_tex = mat.node_tree.nodes['NormalTextureSampler']
					CliffNormalSampler_tex = mat.node_tree.nodes['CliffNormalSampler']
					RGBOverlayTextureSampler_tex = mat.node_tree.nodes['RGBOverlayTextureSampler']

					uv_map_node2 = mat.node_tree.nodes.new(type='ShaderNodeUVMap')
					mapping_node5 = mat.node_tree.nodes.new(type='ShaderNodeMapping')

					uv_map_node2.uv_map = "UV3Map"

					Tiling_Ratios_Cliffs = parameters_Data[parameters_Names.index("Tiling_Ratios_Cliffs")]

					mat.node_tree.links.new(uv_map_node2.outputs['UV'], mapping_node5.inputs[0])

					mapping_node5.inputs[3].default_value[0] = Tiling_Ratios_Cliffs[0]*1.0
					mapping_node5.inputs[3].default_value[1] = Tiling_Ratios_Cliffs[1]*1.0

					mat.node_tree.links.new(mapping_node5.outputs['Vector'], CliffTextureSampler_tex.inputs['Vector'])

					mat.node_tree.links.new(CliffTextureSampler_tex.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Base Color'])

					#Normal
					mix_rgb_node11 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')

					mat.node_tree.links.new(mapping_node5.outputs['Vector'], CliffNormalSampler_tex.inputs['Vector'])

					mat.node_tree.links.new(NormalTextureSampler_tex.outputs['Color'], mix_rgb_node11.inputs['Color1'])
					mat.node_tree.links.new(CliffNormalSampler_tex.outputs['Color'], mix_rgb_node11.inputs['Color2'])

					mat.node_tree.links.new(mix_rgb_node11.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Normal'])

					#Shading
					mat.node_tree.nodes[mMaterialId].inputs['Specular'].default_value = 0.1
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 0.8

				elif shader_type == "DiffuseSpecmapNormalMap":
					NormalTextureSampler_tex = mat.node_tree.nodes['NormalTextureSampler']

					mat.node_tree.links.new(NormalTextureSampler_tex.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Normal'])

					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.0
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 0.6

				elif shader_type == "DiffuseSpecmapNormalMap_DirtMap":
					NormalTextureSampler_tex = mat.node_tree.nodes['NormalTextureSampler']

					mat.node_tree.links.new(NormalTextureSampler_tex.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Normal'])

					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.0
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 0.6

				elif shader_type == "DiffuseSpecmapNormalMap_Overlay":
					NormalTextureSampler_tex = mat.node_tree.nodes['NormalTextureSampler']

					mat.node_tree.links.new(NormalTextureSampler_tex.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Normal'])

					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.0
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 0.6

				elif shader_type == "DiffuseSpecNormalMap_1Bit":
					DiffuseTextureSampler_tex = mat.node_tree.nodes['DiffuseTextureSampler']
					NormalTextureSampler_tex = mat.node_tree.nodes['NormalTextureSampler']

					mat.node_tree.links.new(DiffuseTextureSampler_tex.outputs['Alpha'], mat.node_tree.nodes[mMaterialId].inputs['Alpha'])
					mat.node_tree.links.new(NormalTextureSampler_tex.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Normal'])

					mat.blend_method = 'HASHED'
					mat.shadow_method = 'HASHED'

				elif shader_type == "Diffuse_1Bit_Doublesided":
					DiffuseTextureSampler_tex = mat.node_tree.nodes['DiffuseTextureSampler']

					mat.node_tree.links.new(DiffuseTextureSampler_tex.outputs['Alpha'], mat.node_tree.nodes[mMaterialId].inputs['Alpha'])

					mat.blend_method = 'CLIP'
					mat.shadow_method = 'HASHED'

					mat.use_backface_culling = False

					mat.node_tree.nodes[mMaterialId].inputs['Specular'].default_value = 0.0

				elif shader_type == "Diffuse_1Bit_Doublesided_Skin":
					DiffuseTextureSampler_tex = mat.node_tree.nodes['DiffuseTextureSampler']

					mat.node_tree.links.new(DiffuseTextureSampler_tex.outputs['Alpha'], mat.node_tree.nodes[mMaterialId].inputs['Alpha'])

					mat.blend_method = 'HASHED'
					mat.shadow_method = 'HASHED'

					mat.use_backface_culling = False

					mat.node_tree.nodes[mMaterialId].inputs['Specular'].default_value = 0.0

				elif shader_type == "Diffuse_1Bit_Singlesided":
					DiffuseTextureSampler_tex = mat.node_tree.nodes['DiffuseTextureSampler']

					mat.node_tree.links.new(DiffuseTextureSampler_tex.outputs['Alpha'], mat.node_tree.nodes[mMaterialId].inputs['Alpha'])

					mat.blend_method = 'BLEND'
					mat.shadow_method = 'HASHED'

					mat.use_backface_culling = True

					mat.node_tree.nodes[mMaterialId].inputs['Specular'].default_value = 0.0

				elif shader_type == "Diffuse_Greyscale_Doublesided":
					mat.use_backface_culling = False

					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.0
					mat.node_tree.nodes[mMaterialId].inputs['Specular'].default_value = 0.2
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 0.8

				elif shader_type == "Diffuse_Opaque_Singlesided":
					DiffuseTextureSampler_tex = mat.node_tree.nodes['DiffuseTextureSampler']

					mix_rgb_node1 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')

					materialDiffuse = parameters_Data[parameters_Names.index("materialDiffuse")]

					if DiffuseTextureSampler_tex.label in ("4A_4F_48_C0",):
						mix_rgb_node1.blend_type = "OVERLAY"
						#mix_rgb_node1.inputs['Fac'].default_value = 0.5
						mix_rgb_node1.inputs['Color1'].default_value = materialDiffuse

						mat.node_tree.links.new(DiffuseTextureSampler_tex.outputs['Color'], mix_rgb_node1.inputs['Color2'])
						mat.node_tree.links.new(mix_rgb_node1.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Base Color'])
					else:
						mat.node_tree.links.new(DiffuseTextureSampler_tex.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Base Color'])
						mat.node_tree.links.new(DiffuseTextureSampler_tex.outputs['Alpha'], mat.node_tree.nodes[mMaterialId].inputs['Alpha'])

						mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.0
						mat.node_tree.nodes[mMaterialId].inputs['Specular'].default_value = 0.0
						mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 1.0

						mat.blend_method = 'HASHED'
						mat.shadow_method = 'HASHED'

					mat.use_backface_culling = True

				elif shader_type == "Diffuse_Opaque_Singlesided_ObjectAO":
					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.0
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 0.7

				elif shader_type == "Diffuse_Opaque_Singlesided_Skin":
					DiffuseTextureSampler_tex = mat.node_tree.nodes['DiffuseTextureSampler']

					materialDiffuse = parameters_Data[parameters_Names.index("materialDiffuse")]

					mat.node_tree.links.new(DiffuseTextureSampler_tex.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Base Color'])
					mat.use_backface_culling = True

				elif shader_type == "DriveableSurface":
					ColourMap_Sampler_tex = mat.node_tree.nodes['ColourMap_Sampler']
					DetailMap_Diffuse_Sampler_tex = mat.node_tree.nodes['DetailMap_Diffuse_Sampler']
					Crack_AO_Sampler_tex = mat.node_tree.nodes['Crack_AO_Sampler']
					DetailMap_Normal_Sampler_tex = mat.node_tree.nodes['DetailMap_Normal_Sampler']
					Crack_Normal_Sampler_tex = mat.node_tree.nodes['Crack_Normal_Sampler']
					OverlayA_Sampler_tex = mat.node_tree.nodes['OverlayA_Sampler']
					OverlayB_Sampler_tex = mat.node_tree.nodes['OverlayB_Sampler']

					DetailMapUvScale = parameters_Data[parameters_Names.index("DetailMapUvScale")]
					DiffuseA = parameters_Data[parameters_Names.index("DiffuseA")]
					DiffuseB = parameters_Data[parameters_Names.index("DiffuseB")]
					OverlayA_Diffuse = parameters_Data[parameters_Names.index("OverlayA_Diffuse")]
					OverlayB_Diffuse = parameters_Data[parameters_Names.index("OverlayB_Diffuse")]

					mix_rgb_node1 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					mix_rgb_node2 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					uv_map_node1 = mat.node_tree.nodes.new(type='ShaderNodeUVMap')
					uv_map_node2 = mat.node_tree.nodes.new(type='ShaderNodeUVMap')
					mapping_node1 = mat.node_tree.nodes.new(type='ShaderNodeMapping')

					mix_rgb_node1.blend_type = "OVERLAY"
					mix_rgb_node2.blend_type = "OVERLAY"
					uv_map_node1.uv_map = "UVMap"
					uv_map_node2.uv_map = "UV2Map"
					mix_rgb_node2.inputs['Color2'].default_value = OverlayB_Diffuse

					mapping_node1.inputs[3].default_value[0] = DetailMapUvScale[0]*10.0
					mapping_node1.inputs[3].default_value[1] = DetailMapUvScale[1]*100.0

					mat.node_tree.links.new(uv_map_node1.outputs['UV'], mapping_node1.inputs[0])
					mat.node_tree.links.new(uv_map_node2.outputs['UV'], OverlayB_Sampler_tex.inputs['Vector'])

					mat.node_tree.links.new(mapping_node1.outputs['Vector'], DetailMap_Diffuse_Sampler_tex.inputs['Vector'])

					mat.node_tree.links.new(OverlayA_Sampler_tex.outputs['Color'], mix_rgb_node1.inputs['Fac'])
					mat.node_tree.links.new(DetailMap_Diffuse_Sampler_tex.outputs['Color'], mix_rgb_node1.inputs['Color1'])
					mat.node_tree.links.new(ColourMap_Sampler_tex.outputs['Color'], mix_rgb_node1.inputs['Color2'])

					mat.node_tree.links.new(OverlayB_Sampler_tex.outputs['Color'], mix_rgb_node2.inputs['Fac'])
					mat.node_tree.links.new(mix_rgb_node1.outputs['Color'], mix_rgb_node2.inputs['Color1'])
					mat.node_tree.links.new(mix_rgb_node2.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Base Color'])

					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.5
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 0.8

					#Normal
					mix_rgb_node3 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					mapping_node2 = mat.node_tree.nodes.new(type='ShaderNodeMapping')
					normal_map_node1 = mat.node_tree.nodes.new(type='ShaderNodeNormalMap')
					normal_map_node2 = mat.node_tree.nodes.new(type='ShaderNodeNormalMap')
					normal_map_node1.uv_map = "UVMap"
					normal_map_node2.uv_map = "UVMap"
					normal_map_node1.inputs['Strength'].default_value = 0.48
					normal_map_node2.inputs['Strength'].default_value = 0.4

					CrackMap_UScale_VScale_UOffset_VOffset = parameters_Data[parameters_Names.index("CrackMap_UScale_VScale_UOffset_VOffset")]

					mapping_node2.inputs[3].default_value[0] = CrackMap_UScale_VScale_UOffset_VOffset[0]*1.0
					mapping_node2.inputs[3].default_value[1] = CrackMap_UScale_VScale_UOffset_VOffset[1]*1.0

					mat.node_tree.links.new(uv_map_node1.outputs['UV'], mapping_node2.inputs[0])
					mat.node_tree.links.new(mapping_node1.outputs['Vector'], DetailMap_Normal_Sampler_tex.inputs['Vector'])
					mat.node_tree.links.new(mapping_node2.outputs['Vector'], Crack_Normal_Sampler_tex.inputs['Vector'])

					mat.node_tree.links.new(Crack_Normal_Sampler_tex.outputs['Color'], normal_map_node1.inputs['Color'])
					mat.node_tree.links.new(DetailMap_Normal_Sampler_tex.outputs['Color'], normal_map_node2.inputs['Color'])

					mat.node_tree.links.new(normal_map_node1.outputs['Normal'], mix_rgb_node3.inputs['Color1'])
					mat.node_tree.links.new(normal_map_node2.outputs['Normal'], mix_rgb_node3.inputs['Color2'])
					mat.node_tree.links.new(mix_rgb_node3.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Normal'])

				elif shader_type == "DriveableSurface_Car_Select_Simple":
					ColourMap_Sampler_tex = mat.node_tree.nodes['ColourMap_Sampler']
					DetailMap_Normal_Sampler_tex = mat.node_tree.nodes['DetailMap_Normal_Sampler']

					mix_rgb_node1 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')

					mix_rgb_node1.blend_type = "OVERLAY"

					mat.node_tree.links.new(ColourMap_Sampler_tex.outputs['Alpha'], mix_rgb_node1.inputs['Fac'])
					mat.node_tree.links.new(ColourMap_Sampler_tex.outputs['Color'], mix_rgb_node1.inputs['Color1'])
					mat.node_tree.links.new(mix_rgb_node1.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Base Color'])

					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.6
					mat.node_tree.nodes[mMaterialId].inputs['Specular'].default_value = 0.0
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 0.1

					normal_map_node1 = mat.node_tree.nodes.new(type='ShaderNodeNormalMap')
					normal_map_node1.uv_map = "UVMap"

					mat.node_tree.links.new(DetailMap_Normal_Sampler_tex.outputs['Color'], normal_map_node1.inputs['Color'])
					mat.node_tree.links.new(normal_map_node1.outputs['Normal'], mat.node_tree.nodes[mMaterialId].inputs['Normal'])

				elif shader_type == "DriveableSurface_Car_Select":
					ColourMap_Sampler_tex = mat.node_tree.nodes['ColourMap_Sampler']
					DetailMap_Diffuse_Sampler_tex = mat.node_tree.nodes['DetailMap_Diffuse_Sampler']
					Crack_AO_Sampler_tex = mat.node_tree.nodes['Crack_AO_Sampler']
					DetailMap_Normal_Sampler_tex = mat.node_tree.nodes['DetailMap_Normal_Sampler']
					Crack_Normal_Sampler_tex = mat.node_tree.nodes['Crack_Normal_Sampler']
					OverlayA_Sampler_tex = mat.node_tree.nodes['OverlayA_Sampler']
					OverlayB_Sampler_tex = mat.node_tree.nodes['OverlayB_Sampler']

					DetailMapUvScale = parameters_Data[parameters_Names.index("DetailMapUvScale")]
					DiffuseA = parameters_Data[parameters_Names.index("DiffuseA")]
					DiffuseB = parameters_Data[parameters_Names.index("DiffuseB")]
					OverlayA_Diffuse = parameters_Data[parameters_Names.index("OverlayA_Diffuse")]
					OverlayB_Diffuse = parameters_Data[parameters_Names.index("OverlayB_Diffuse")]

					mix_rgb_node1 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					mix_rgb_node2 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					uv_map_node1 = mat.node_tree.nodes.new(type='ShaderNodeUVMap')
					uv_map_node2 = mat.node_tree.nodes.new(type='ShaderNodeUVMap')
					mapping_node1 = mat.node_tree.nodes.new(type='ShaderNodeMapping')

					mix_rgb_node1.blend_type = "OVERLAY"
					mix_rgb_node2.blend_type = "OVERLAY"
					uv_map_node1.uv_map = "UVMap"
					uv_map_node2.uv_map = "UV4Map"
					mix_rgb_node2.inputs['Color2'].default_value = OverlayB_Diffuse

					mapping_node1.inputs[3].default_value[0] = DetailMapUvScale[0]*1.0
					mapping_node1.inputs[3].default_value[1] = DetailMapUvScale[1]*1.0

					mat.node_tree.links.new(uv_map_node1.outputs['UV'], mapping_node1.inputs[0])
					mat.node_tree.links.new(mapping_node1.outputs['Vector'], DetailMap_Diffuse_Sampler_tex.inputs['Vector'])

					mat.node_tree.links.new(uv_map_node2.outputs['UV'], OverlayA_Sampler_tex.inputs['Vector'])

					mat.node_tree.links.new(OverlayA_Sampler_tex.outputs['Color'], mix_rgb_node1.inputs['Fac'])
					mat.node_tree.links.new(DetailMap_Diffuse_Sampler_tex.outputs['Color'], mix_rgb_node1.inputs['Color1'])
					mat.node_tree.links.new(ColourMap_Sampler_tex.outputs['Color'], mix_rgb_node1.inputs['Color2'])

					mat.node_tree.links.new(OverlayB_Sampler_tex.outputs['Color'], mix_rgb_node2.inputs['Fac'])
					mat.node_tree.links.new(mix_rgb_node1.outputs['Color'], mix_rgb_node2.inputs['Color1'])
					mat.node_tree.links.new(mix_rgb_node2.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Base Color'])

					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.6
					mat.node_tree.nodes[mMaterialId].inputs['Specular'].default_value = 0.0
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 0.1

					#Normal
					mix_rgb_node3 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					mapping_node2 = mat.node_tree.nodes.new(type='ShaderNodeMapping')
					normal_map_node1 = mat.node_tree.nodes.new(type='ShaderNodeNormalMap')
					normal_map_node2 = mat.node_tree.nodes.new(type='ShaderNodeNormalMap')
					normal_map_node1.uv_map = "UVMap"
					normal_map_node2.uv_map = "UVMap"
					normal_map_node1.inputs['Strength'].default_value = 0.48
					normal_map_node2.inputs['Strength'].default_value = 0.4

					CrackMap_UScale_VScale_UOffset_VOffset = parameters_Data[parameters_Names.index("CrackMap_UScale_VScale_UOffset_VOffset")]

					mapping_node2.inputs[3].default_value[0] = CrackMap_UScale_VScale_UOffset_VOffset[0]*1.0
					mapping_node2.inputs[3].default_value[1] = CrackMap_UScale_VScale_UOffset_VOffset[1]*1.0

					mat.node_tree.links.new(uv_map_node1.outputs['UV'], mapping_node2.inputs[0])
					mat.node_tree.links.new(mapping_node1.outputs['Vector'], DetailMap_Normal_Sampler_tex.inputs['Vector'])
					mat.node_tree.links.new(mapping_node2.outputs['Vector'], Crack_Normal_Sampler_tex.inputs['Vector'])

					mat.node_tree.links.new(Crack_Normal_Sampler_tex.outputs['Color'], normal_map_node1.inputs['Color'])
					mat.node_tree.links.new(DetailMap_Normal_Sampler_tex.outputs['Color'], normal_map_node2.inputs['Color'])

					mat.node_tree.links.new(normal_map_node1.outputs['Normal'], mix_rgb_node3.inputs['Color1'])
					mat.node_tree.links.new(normal_map_node2.outputs['Normal'], mix_rgb_node3.inputs['Color2'])
					mat.node_tree.links.new(mix_rgb_node3.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Normal'])

				elif shader_type == "DriveableSurface_CarPark":
					ColourMap_Sampler_tex = mat.node_tree.nodes['ColourMap_Sampler']
					DetailMap_Diffuse_Sampler_tex = mat.node_tree.nodes['DetailMap_Diffuse_Sampler']
					Crack_AO_Sampler_tex = mat.node_tree.nodes['Crack_AO_Sampler']
					DetailMap_Normal_Sampler_tex = mat.node_tree.nodes['DetailMap_Normal_Sampler']
					Crack_Normal_Sampler_tex = mat.node_tree.nodes['Crack_Normal_Sampler']
					OverlayA_Sampler_tex = mat.node_tree.nodes['OverlayA_Sampler']
					OverlayB_Sampler_tex = mat.node_tree.nodes['OverlayB_Sampler']

					DetailMapUvScale = parameters_Data[parameters_Names.index("DetailMapUvScale")]
					DiffuseA = parameters_Data[parameters_Names.index("DiffuseA")]
					DiffuseB = parameters_Data[parameters_Names.index("DiffuseB")]
					OverlayA_Diffuse = parameters_Data[parameters_Names.index("OverlayA_Diffuse")]
					OverlayB_Diffuse = parameters_Data[parameters_Names.index("OverlayB_Diffuse")]

					mix_rgb_node1 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					mix_rgb_node2 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					uv_map_node1 = mat.node_tree.nodes.new(type='ShaderNodeUVMap')
					uv_map_node2 = mat.node_tree.nodes.new(type='ShaderNodeUVMap')
					mapping_node1 = mat.node_tree.nodes.new(type='ShaderNodeMapping')

					mix_rgb_node1.blend_type = "OVERLAY"
					mix_rgb_node2.blend_type = "OVERLAY"
					uv_map_node1.uv_map = "UVMap"
					uv_map_node2.uv_map = "UV4Map"
					mix_rgb_node2.inputs['Color2'].default_value = OverlayB_Diffuse

					mapping_node1.inputs[3].default_value[0] = DetailMapUvScale[0]*1.0
					mapping_node1.inputs[3].default_value[1] = DetailMapUvScale[1]*1.0

					mat.node_tree.links.new(uv_map_node1.outputs['UV'], mapping_node1.inputs[0])
					mat.node_tree.links.new(mapping_node1.outputs['Vector'], DetailMap_Diffuse_Sampler_tex.inputs['Vector'])

					mat.node_tree.links.new(uv_map_node2.outputs['UV'], OverlayA_Sampler_tex.inputs['Vector'])

					mat.node_tree.links.new(OverlayA_Sampler_tex.outputs['Color'], mix_rgb_node1.inputs['Fac'])
					mat.node_tree.links.new(DetailMap_Diffuse_Sampler_tex.outputs['Color'], mix_rgb_node1.inputs['Color1'])
					mat.node_tree.links.new(ColourMap_Sampler_tex.outputs['Color'], mix_rgb_node1.inputs['Color2'])

					mat.node_tree.links.new(OverlayB_Sampler_tex.outputs['Color'], mix_rgb_node2.inputs['Fac'])
					mat.node_tree.links.new(mix_rgb_node1.outputs['Color'], mix_rgb_node2.inputs['Color1'])
					mat.node_tree.links.new(mix_rgb_node2.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Base Color'])

					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.2
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 1.0

					#Normal
					mix_rgb_node3 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					mapping_node2 = mat.node_tree.nodes.new(type='ShaderNodeMapping')
					normal_map_node1 = mat.node_tree.nodes.new(type='ShaderNodeNormalMap')
					normal_map_node2 = mat.node_tree.nodes.new(type='ShaderNodeNormalMap')
					normal_map_node1.uv_map = "UVMap"
					normal_map_node2.uv_map = "UVMap"
					normal_map_node1.inputs['Strength'].default_value = 0.48
					normal_map_node2.inputs['Strength'].default_value = 0.4

					CrackMap_UScale_VScale_UOffset_VOffset = parameters_Data[parameters_Names.index("CrackMap_UScale_VScale_UOffset_VOffset")]

					mapping_node2.inputs[3].default_value[0] = CrackMap_UScale_VScale_UOffset_VOffset[0]*1.0
					mapping_node2.inputs[3].default_value[1] = CrackMap_UScale_VScale_UOffset_VOffset[1]*1.0

					mat.node_tree.links.new(uv_map_node1.outputs['UV'], mapping_node2.inputs[0])
					mat.node_tree.links.new(mapping_node1.outputs['Vector'], DetailMap_Normal_Sampler_tex.inputs['Vector'])
					mat.node_tree.links.new(mapping_node2.outputs['Vector'], Crack_Normal_Sampler_tex.inputs['Vector'])

					mat.node_tree.links.new(Crack_Normal_Sampler_tex.outputs['Color'], normal_map_node1.inputs['Color'])
					mat.node_tree.links.new(DetailMap_Normal_Sampler_tex.outputs['Color'], normal_map_node2.inputs['Color'])

					mat.node_tree.links.new(normal_map_node1.outputs['Normal'], mix_rgb_node3.inputs['Color1'])
					mat.node_tree.links.new(normal_map_node2.outputs['Normal'], mix_rgb_node3.inputs['Color2'])
					mat.node_tree.links.new(mix_rgb_node3.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Normal'])

				elif shader_type == "DriveableSurface_Decal_CarPark":
					ColourMap_Sampler_tex = mat.node_tree.nodes['ColourMap_Sampler']
					DetailMap_Diffuse_Sampler_tex = mat.node_tree.nodes['DetailMap_Diffuse_Sampler']
					Crack_AO_Sampler_tex = mat.node_tree.nodes['Crack_AO_Sampler']
					DetailMap_Normal_Sampler_tex = mat.node_tree.nodes['DetailMap_Normal_Sampler']
					Crack_Normal_Sampler_tex = mat.node_tree.nodes['Crack_Normal_Sampler']
					OverlayA_Sampler_tex = mat.node_tree.nodes['OverlayA_Sampler']
					OverlayB_Sampler_tex = mat.node_tree.nodes['OverlayB_Sampler']
					Decal_Diffuse_Sampler_tex = mat.node_tree.nodes['Decal_Diffuse_Sampler']

					DetailMapUvScale = parameters_Data[parameters_Names.index("DetailMapUvScale")]
					DiffuseA = parameters_Data[parameters_Names.index("DiffuseA")]
					DiffuseB = parameters_Data[parameters_Names.index("DiffuseB")]
					OverlayA_Diffuse = parameters_Data[parameters_Names.index("OverlayA_Diffuse")]
					OverlayB_Diffuse = parameters_Data[parameters_Names.index("OverlayB_Diffuse")]

					mix_rgb_node1 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					mix_rgb_node2 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					mix_rgb_node3 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					uv_map_node1 = mat.node_tree.nodes.new(type='ShaderNodeUVMap')
					uv_map_node2 = mat.node_tree.nodes.new(type='ShaderNodeUVMap')
					uv_map_node3 = mat.node_tree.nodes.new(type='ShaderNodeUVMap')
					mapping_node1 = mat.node_tree.nodes.new(type='ShaderNodeMapping')

					mix_rgb_node1.blend_type = "OVERLAY"
					mix_rgb_node2.blend_type = "OVERLAY"
					mix_rgb_node3.blend_type = "MIX"
					uv_map_node1.uv_map = "UVMap"
					uv_map_node2.uv_map = "UV4Map"
					uv_map_node3.uv_map = "UV3Map"
					mix_rgb_node2.inputs['Color2'].default_value = OverlayB_Diffuse

					mapping_node1.inputs[3].default_value[0] = DetailMapUvScale[0]*1.0
					mapping_node1.inputs[3].default_value[1] = DetailMapUvScale[1]*1.0

					mat.node_tree.links.new(uv_map_node1.outputs['UV'], mapping_node1.inputs[0])
					mat.node_tree.links.new(mapping_node1.outputs['Vector'], DetailMap_Diffuse_Sampler_tex.inputs['Vector'])

					mat.node_tree.links.new(uv_map_node2.outputs['UV'], OverlayA_Sampler_tex.inputs['Vector'])
					mat.node_tree.links.new(uv_map_node3.outputs['UV'], Decal_Diffuse_Sampler_tex.inputs['Vector'])

					mat.node_tree.links.new(OverlayA_Sampler_tex.outputs['Color'], mix_rgb_node1.inputs['Fac'])
					mat.node_tree.links.new(DetailMap_Diffuse_Sampler_tex.outputs['Color'], mix_rgb_node1.inputs['Color1'])
					mat.node_tree.links.new(ColourMap_Sampler_tex.outputs['Color'], mix_rgb_node1.inputs['Color2'])

					mat.node_tree.links.new(OverlayB_Sampler_tex.outputs['Color'], mix_rgb_node2.inputs['Fac'])
					mat.node_tree.links.new(mix_rgb_node1.outputs['Color'], mix_rgb_node2.inputs['Color1'])
					mat.node_tree.links.new(mix_rgb_node2.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Base Color'])

					mat.node_tree.links.new(Decal_Diffuse_Sampler_tex.outputs['Alpha'], mix_rgb_node3.inputs['Fac'])
					mat.node_tree.links.new(mix_rgb_node2.outputs['Color'], mix_rgb_node3.inputs['Color1'])
					mat.node_tree.links.new(Decal_Diffuse_Sampler_tex.outputs['Color'], mix_rgb_node3.inputs['Color2'])

					mat.node_tree.links.new(mix_rgb_node3.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Base Color'])

					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.2
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 1.0

					#Normal
					mix_rgb_node11 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					mapping_node2 = mat.node_tree.nodes.new(type='ShaderNodeMapping')
					normal_map_node1 = mat.node_tree.nodes.new(type='ShaderNodeNormalMap')
					normal_map_node2 = mat.node_tree.nodes.new(type='ShaderNodeNormalMap')
					normal_map_node1.uv_map = "UVMap"
					normal_map_node2.uv_map = "UVMap"
					normal_map_node1.inputs['Strength'].default_value = 0.48
					normal_map_node2.inputs['Strength'].default_value = 0.4

					CrackMap_UScale_VScale_UOffset_VOffset = parameters_Data[parameters_Names.index("CrackMap_UScale_VScale_UOffset_VOffset")]

					mapping_node2.inputs[3].default_value[0] = CrackMap_UScale_VScale_UOffset_VOffset[0]*1.0
					mapping_node2.inputs[3].default_value[1] = CrackMap_UScale_VScale_UOffset_VOffset[1]*1.0

					mat.node_tree.links.new(uv_map_node1.outputs['UV'], mapping_node2.inputs[0])
					mat.node_tree.links.new(mapping_node1.outputs['Vector'], DetailMap_Normal_Sampler_tex.inputs['Vector'])
					mat.node_tree.links.new(mapping_node2.outputs['Vector'], Crack_Normal_Sampler_tex.inputs['Vector'])

					mat.node_tree.links.new(Crack_Normal_Sampler_tex.outputs['Color'], normal_map_node1.inputs['Color'])
					mat.node_tree.links.new(DetailMap_Normal_Sampler_tex.outputs['Color'], normal_map_node2.inputs['Color'])

					mat.node_tree.links.new(normal_map_node1.outputs['Normal'], mix_rgb_node11.inputs['Color1'])
					mat.node_tree.links.new(normal_map_node2.outputs['Normal'], mix_rgb_node11.inputs['Color2'])
					mat.node_tree.links.new(mix_rgb_node11.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Normal'])

				elif shader_type == "DriveableSurface_AlphaMask":
					ColourMap_Sampler_tex = mat.node_tree.nodes['ColourMap_Sampler']
					DetailMap_Diffuse_Sampler_tex = mat.node_tree.nodes['DetailMap_Diffuse_Sampler']
					Crack_AO_Sampler_tex = mat.node_tree.nodes['Crack_AO_Sampler']
					DetailMap_Normal_Sampler_tex = mat.node_tree.nodes['DetailMap_Normal_Sampler']
					Crack_Normal_Sampler_tex = mat.node_tree.nodes['Crack_Normal_Sampler']
					OverlayA_Sampler_tex = mat.node_tree.nodes['OverlayA_Sampler']
					OverlayB_Sampler_tex = mat.node_tree.nodes['OverlayB_Sampler']
					EdgeAlphaPlusAoMap_Sampler_tex = mat.node_tree.nodes['EdgeAlphaPlusAoMap_Sampler']

					DetailMapUvScale = parameters_Data[parameters_Names.index("DetailMapUvScale")]
					DiffuseA = parameters_Data[parameters_Names.index("DiffuseA")]
					DiffuseB = parameters_Data[parameters_Names.index("DiffuseB")]
					OverlayA_Diffuse = parameters_Data[parameters_Names.index("OverlayA_Diffuse")]
					OverlayB_Diffuse = parameters_Data[parameters_Names.index("OverlayB_Diffuse")]

					mix_rgb_node1 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					mix_rgb_node2 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					uv_map_node1 = mat.node_tree.nodes.new(type='ShaderNodeUVMap')
					uv_map_node2 = mat.node_tree.nodes.new(type='ShaderNodeUVMap')
					mapping_node1 = mat.node_tree.nodes.new(type='ShaderNodeMapping')
					separate_rgb_node1 = mat.node_tree.nodes.new(type='ShaderNodeSeparateRGB')

					mix_rgb_node1.blend_type = "OVERLAY"
					mix_rgb_node2.blend_type = "OVERLAY"
					uv_map_node1.uv_map = "UVMap"
					uv_map_node2.uv_map = "UV3Map"
					mix_rgb_node2.inputs['Color2'].default_value = OverlayB_Diffuse

					mapping_node1.inputs[3].default_value[0] = DetailMapUvScale[0]*10.0
					mapping_node1.inputs[3].default_value[1] = DetailMapUvScale[1]*100.0

					mat.node_tree.links.new(uv_map_node1.outputs['UV'], mapping_node1.inputs[0])
					mat.node_tree.links.new(mapping_node1.outputs['Vector'], DetailMap_Diffuse_Sampler_tex.inputs['Vector'])

					mat.node_tree.links.new(OverlayA_Sampler_tex.outputs['Color'], mix_rgb_node1.inputs['Fac'])
					mat.node_tree.links.new(DetailMap_Diffuse_Sampler_tex.outputs['Color'], mix_rgb_node1.inputs['Color1'])
					mat.node_tree.links.new(ColourMap_Sampler_tex.outputs['Color'], mix_rgb_node1.inputs['Color2'])

					mat.node_tree.links.new(OverlayB_Sampler_tex.outputs['Color'], mix_rgb_node2.inputs['Fac'])
					mat.node_tree.links.new(mix_rgb_node1.outputs['Color'], mix_rgb_node2.inputs['Color1'])
					mat.node_tree.links.new(mix_rgb_node2.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Base Color'])

					mat.node_tree.links.new(uv_map_node2.outputs['UV'], EdgeAlphaPlusAoMap_Sampler_tex.inputs['Vector'])
					mat.node_tree.links.new(EdgeAlphaPlusAoMap_Sampler_tex.outputs['Color'], separate_rgb_node1.inputs['Image'])
					mat.node_tree.links.new(separate_rgb_node1.outputs['R'], mat.node_tree.nodes[mMaterialId].inputs['Alpha'])

					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.2
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 1.0

					#Normal
					mix_rgb_node3 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					mapping_node2 = mat.node_tree.nodes.new(type='ShaderNodeMapping')
					normal_map_node1 = mat.node_tree.nodes.new(type='ShaderNodeNormalMap')
					normal_map_node2 = mat.node_tree.nodes.new(type='ShaderNodeNormalMap')
					normal_map_node1.uv_map = "UVMap"
					normal_map_node2.uv_map = "UVMap"
					normal_map_node1.inputs['Strength'].default_value = 0.48
					normal_map_node2.inputs['Strength'].default_value = 0.4

					CrackMap_UScale_VScale_UOffset_VOffset = parameters_Data[parameters_Names.index("CrackMap_UScale_VScale_UOffset_VOffset")]

					mapping_node2.inputs[3].default_value[0] = CrackMap_UScale_VScale_UOffset_VOffset[0]*1.0
					mapping_node2.inputs[3].default_value[1] = CrackMap_UScale_VScale_UOffset_VOffset[1]*1.0

					mat.node_tree.links.new(uv_map_node1.outputs['UV'], mapping_node2.inputs[0])
					mat.node_tree.links.new(mapping_node1.outputs['Vector'], DetailMap_Normal_Sampler_tex.inputs['Vector'])
					mat.node_tree.links.new(mapping_node2.outputs['Vector'], Crack_Normal_Sampler_tex.inputs['Vector'])

					mat.node_tree.links.new(Crack_Normal_Sampler_tex.outputs['Color'], normal_map_node1.inputs['Color'])
					mat.node_tree.links.new(DetailMap_Normal_Sampler_tex.outputs['Color'], normal_map_node2.inputs['Color'])

					mat.node_tree.links.new(normal_map_node1.outputs['Normal'], mix_rgb_node3.inputs['Color1'])
					mat.node_tree.links.new(normal_map_node2.outputs['Normal'], mix_rgb_node3.inputs['Color2'])
					mat.node_tree.links.new(mix_rgb_node3.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Normal'])

					mat.blend_method = 'BLEND'
					mat.shadow_method = 'HASHED'

				elif shader_type == "DriveableSurface_AlphaMask_Lightmap":
					ColourMap_Sampler_tex = mat.node_tree.nodes['ColourMap_Sampler']
					DetailMap_Diffuse_Sampler_tex = mat.node_tree.nodes['DetailMap_Diffuse_Sampler']
					EdgeAlphaPlusAoMap_Sampler_tex = mat.node_tree.nodes['EdgeAlphaPlusAoMap_Sampler']
					Crack_Normal_Sampler_tex = mat.node_tree.nodes['Crack_Normal_Sampler']
					DetailMap_Normal_Sampler_tex = mat.node_tree.nodes['DetailMap_Normal_Sampler']

					mix_rgb_node1 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					uv_map_node1 = mat.node_tree.nodes.new(type='ShaderNodeUVMap')
					uv_map_node2 = mat.node_tree.nodes.new(type='ShaderNodeUVMap')
					mapping_node = mat.node_tree.nodes.new(type='ShaderNodeMapping')
					separate_rgb_node1 = mat.node_tree.nodes.new(type='ShaderNodeSeparateRGB')

					uv_map_node1.uv_map = "UVMap"
					uv_map_node2.uv_map = "UV3Map"

					DetailMapUvScale = parameters_Data[parameters_Names.index("DetailMapUvScale")]

					mapping_node.inputs[3].default_value[0] = DetailMapUvScale[0]*10.0
					mapping_node.inputs[3].default_value[1] = DetailMapUvScale[1]*10.0

					mat.node_tree.links.new(uv_map_node1.outputs['UV'], mapping_node.inputs[0])
					mat.node_tree.links.new(mapping_node.outputs['Vector'], DetailMap_Diffuse_Sampler_tex.inputs['Vector'])
					mat.node_tree.links.new(ColourMap_Sampler_tex.outputs['Color'], mix_rgb_node1.inputs['Color1'])
					mat.node_tree.links.new(DetailMap_Diffuse_Sampler_tex.outputs['Color'], mix_rgb_node1.inputs['Color2'])

					mat.node_tree.links.new(uv_map_node2.outputs['UV'], EdgeAlphaPlusAoMap_Sampler_tex.inputs['Vector'])
					mat.node_tree.links.new(EdgeAlphaPlusAoMap_Sampler_tex.outputs['Color'], separate_rgb_node1.inputs['Image'])
					mat.node_tree.links.new(separate_rgb_node1.outputs['G'], mat.node_tree.nodes[mMaterialId].inputs['Alpha'])

					mat.node_tree.links.new(mix_rgb_node1.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Base Color'])
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 0.5
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 0.5

					mat.blend_method = 'BLEND'
					mat.shadow_method = 'HASHED'

					mix_rgb_node3 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					normal_map_node1 = mat.node_tree.nodes.new(type='ShaderNodeNormalMap')
					normal_map_node2 = mat.node_tree.nodes.new(type='ShaderNodeNormalMap')
					normal_map_node1.uv_map = "UVMap"
					normal_map_node2.uv_map = "UVMap"

					mat.node_tree.links.new(mapping_node.outputs['Vector'], DetailMap_Normal_Sampler_tex.inputs['Vector'])
					mat.node_tree.links.new(Crack_Normal_Sampler_tex.outputs['Color'], normal_map_node1.inputs['Color'])
					mat.node_tree.links.new(DetailMap_Normal_Sampler_tex.outputs['Color'], normal_map_node2.inputs['Color'])

					mat.node_tree.links.new(normal_map_node1.outputs['Normal'], mix_rgb_node3.inputs['Color1'])
					mat.node_tree.links.new(normal_map_node2.outputs['Normal'], mix_rgb_node3.inputs['Color2'])
					mat.node_tree.links.new(mix_rgb_node3.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Normal'])

				elif shader_type == "DriveableSurface_AlphaMask_CarPark":
					ColourMap_Sampler_tex = mat.node_tree.nodes['ColourMap_Sampler']
					DetailMap_Diffuse_Sampler_tex = mat.node_tree.nodes['DetailMap_Diffuse_Sampler']
					Crack_AO_Sampler_tex = mat.node_tree.nodes['Crack_AO_Sampler']
					DetailMap_Normal_Sampler_tex = mat.node_tree.nodes['DetailMap_Normal_Sampler']
					Crack_Normal_Sampler_tex = mat.node_tree.nodes['Crack_Normal_Sampler']
					OverlayA_Sampler_tex = mat.node_tree.nodes['OverlayA_Sampler']
					OverlayB_Sampler_tex = mat.node_tree.nodes['OverlayB_Sampler']
					EdgeAlphaPlusAoMap_Sampler_tex = mat.node_tree.nodes['EdgeAlphaPlusAoMap_Sampler']

					DetailMapUvScale = parameters_Data[parameters_Names.index("DetailMapUvScale")]
					DiffuseA = parameters_Data[parameters_Names.index("DiffuseA")]
					DiffuseB = parameters_Data[parameters_Names.index("DiffuseB")]
					OverlayA_Diffuse = parameters_Data[parameters_Names.index("OverlayA_Diffuse")]
					OverlayB_Diffuse = parameters_Data[parameters_Names.index("OverlayB_Diffuse")]

					mix_rgb_node1 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					mix_rgb_node2 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					uv_map_node1 = mat.node_tree.nodes.new(type='ShaderNodeUVMap')
					uv_map_node2 = mat.node_tree.nodes.new(type='ShaderNodeUVMap')
					uv_map_node3 = mat.node_tree.nodes.new(type='ShaderNodeUVMap')
					mapping_node1 = mat.node_tree.nodes.new(type='ShaderNodeMapping')
					separate_rgb_node1 = mat.node_tree.nodes.new(type='ShaderNodeSeparateRGB')

					mix_rgb_node1.blend_type = "OVERLAY"
					mix_rgb_node2.blend_type = "OVERLAY"
					uv_map_node1.uv_map = "UVMap"
					uv_map_node2.uv_map = "UV4Map"
					uv_map_node3.uv_map = "UV3Map"
					mix_rgb_node2.inputs['Color2'].default_value = OverlayB_Diffuse

					mapping_node1.inputs[3].default_value[0] = DetailMapUvScale[0]*1.0
					mapping_node1.inputs[3].default_value[1] = DetailMapUvScale[1]*1.0

					mat.node_tree.links.new(uv_map_node1.outputs['UV'], mapping_node1.inputs[0])
					mat.node_tree.links.new(mapping_node1.outputs['Vector'], DetailMap_Diffuse_Sampler_tex.inputs['Vector'])

					mat.node_tree.links.new(uv_map_node2.outputs['UV'], OverlayA_Sampler_tex.inputs['Vector'])

					mat.node_tree.links.new(OverlayA_Sampler_tex.outputs['Color'], mix_rgb_node1.inputs['Fac'])
					mat.node_tree.links.new(DetailMap_Diffuse_Sampler_tex.outputs['Color'], mix_rgb_node1.inputs['Color1'])
					mat.node_tree.links.new(ColourMap_Sampler_tex.outputs['Color'], mix_rgb_node1.inputs['Color2'])

					mat.node_tree.links.new(OverlayB_Sampler_tex.outputs['Color'], mix_rgb_node2.inputs['Fac'])
					mat.node_tree.links.new(mix_rgb_node1.outputs['Color'], mix_rgb_node2.inputs['Color1'])
					mat.node_tree.links.new(mix_rgb_node2.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Base Color'])

					mat.node_tree.links.new(uv_map_node3.outputs['UV'], EdgeAlphaPlusAoMap_Sampler_tex.inputs['Vector'])
					mat.node_tree.links.new(EdgeAlphaPlusAoMap_Sampler_tex.outputs['Color'], separate_rgb_node1.inputs['Image'])
					mat.node_tree.links.new(separate_rgb_node1.outputs['G'], mat.node_tree.nodes[mMaterialId].inputs['Alpha'])

					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.2
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 1.0

					#Normal
					mix_rgb_node3 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					mapping_node2 = mat.node_tree.nodes.new(type='ShaderNodeMapping')
					normal_map_node1 = mat.node_tree.nodes.new(type='ShaderNodeNormalMap')
					normal_map_node2 = mat.node_tree.nodes.new(type='ShaderNodeNormalMap')
					normal_map_node1.uv_map = "UVMap"
					normal_map_node2.uv_map = "UVMap"
					normal_map_node1.inputs['Strength'].default_value = 0.48
					normal_map_node2.inputs['Strength'].default_value = 0.4

					CrackMap_UScale_VScale_UOffset_VOffset = parameters_Data[parameters_Names.index("CrackMap_UScale_VScale_UOffset_VOffset")]

					mapping_node2.inputs[3].default_value[0] = CrackMap_UScale_VScale_UOffset_VOffset[0]*1.0
					mapping_node2.inputs[3].default_value[1] = CrackMap_UScale_VScale_UOffset_VOffset[1]*1.0

					mat.node_tree.links.new(uv_map_node1.outputs['UV'], mapping_node2.inputs[0])
					mat.node_tree.links.new(mapping_node1.outputs['Vector'], DetailMap_Normal_Sampler_tex.inputs['Vector'])
					mat.node_tree.links.new(mapping_node2.outputs['Vector'], Crack_Normal_Sampler_tex.inputs['Vector'])

					mat.node_tree.links.new(Crack_Normal_Sampler_tex.outputs['Color'], normal_map_node1.inputs['Color'])
					mat.node_tree.links.new(DetailMap_Normal_Sampler_tex.outputs['Color'], normal_map_node2.inputs['Color'])

					mat.node_tree.links.new(normal_map_node1.outputs['Normal'], mix_rgb_node3.inputs['Color1'])
					mat.node_tree.links.new(normal_map_node2.outputs['Normal'], mix_rgb_node3.inputs['Color2'])
					mat.node_tree.links.new(mix_rgb_node3.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Normal'])

					mat.blend_method = 'BLEND'
					mat.shadow_method = 'HASHED'

				elif shader_type == "DriveableSurface_Decal":
					ColourMap_Sampler_tex = mat.node_tree.nodes['ColourMap_Sampler']
					DetailMap_Diffuse_Sampler_tex = mat.node_tree.nodes['DetailMap_Diffuse_Sampler']
					Crack_AO_Sampler_tex = mat.node_tree.nodes['Crack_AO_Sampler']
					DetailMap_Normal_Sampler_tex = mat.node_tree.nodes['DetailMap_Normal_Sampler']
					Crack_Normal_Sampler_tex = mat.node_tree.nodes['Crack_Normal_Sampler']
					OverlayA_Sampler_tex = mat.node_tree.nodes['OverlayA_Sampler']
					OverlayB_Sampler_tex = mat.node_tree.nodes['OverlayB_Sampler']
					Decal_Diffuse_Sampler_tex = mat.node_tree.nodes['Decal_Diffuse_Sampler']

					DetailMapUvScale = parameters_Data[parameters_Names.index("DetailMapUvScale")]
					DiffuseA = parameters_Data[parameters_Names.index("DiffuseA")]
					DiffuseB = parameters_Data[parameters_Names.index("DiffuseB")]
					OverlayA_Diffuse = parameters_Data[parameters_Names.index("OverlayA_Diffuse")]
					OverlayB_Diffuse = parameters_Data[parameters_Names.index("OverlayB_Diffuse")]

					mix_rgb_node1 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					mix_rgb_node2 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					mix_rgb_node3 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					mix_rgb_node4 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					uv_map_node1 = mat.node_tree.nodes.new(type='ShaderNodeUVMap')
					uv_map_node2 = mat.node_tree.nodes.new(type='ShaderNodeUVMap')
					mapping_node1 = mat.node_tree.nodes.new(type='ShaderNodeMapping')

					mix_rgb_node1.blend_type = "OVERLAY"
					mix_rgb_node2.blend_type = "OVERLAY"
					mix_rgb_node3.blend_type = "OVERLAY"
					mix_rgb_node4.blend_type = "MIX"
					uv_map_node1.uv_map = "UVMap"
					uv_map_node2.uv_map = "UV3Map"
					mix_rgb_node2.inputs['Color2'].default_value = OverlayB_Diffuse

					mapping_node1.inputs[3].default_value[0] = DetailMapUvScale[0]*10.0
					mapping_node1.inputs[3].default_value[1] = DetailMapUvScale[1]*100.0

					mat.node_tree.links.new(uv_map_node1.outputs['UV'], mapping_node1.inputs[0])
					mat.node_tree.links.new(mapping_node1.outputs['Vector'], DetailMap_Diffuse_Sampler_tex.inputs['Vector'])

					mat.node_tree.links.new(OverlayA_Sampler_tex.outputs['Color'], mix_rgb_node1.inputs['Fac'])
					mat.node_tree.links.new(DetailMap_Diffuse_Sampler_tex.outputs['Color'], mix_rgb_node1.inputs['Color1'])
					mat.node_tree.links.new(ColourMap_Sampler_tex.outputs['Color'], mix_rgb_node1.inputs['Color2'])

					mat.node_tree.links.new(OverlayB_Sampler_tex.outputs['Color'], mix_rgb_node2.inputs['Fac'])
					mat.node_tree.links.new(mix_rgb_node1.outputs['Color'], mix_rgb_node2.inputs['Color1'])


					mat.node_tree.links.new(uv_map_node2.outputs['UV'], Decal_Diffuse_Sampler_tex.inputs['Vector'])
					mat.node_tree.links.new(Decal_Diffuse_Sampler_tex.outputs['Color'], mix_rgb_node3.inputs['Color1'])
					mat.node_tree.links.new(Decal_Diffuse_Sampler_tex.outputs['Alpha'], mix_rgb_node3.inputs['Fac'])

					mat.node_tree.links.new(Decal_Diffuse_Sampler_tex.outputs['Alpha'], mix_rgb_node4.inputs['Fac'])
					mat.node_tree.links.new(mix_rgb_node2.outputs['Color'], mix_rgb_node4.inputs['Color1'])
					mat.node_tree.links.new(mix_rgb_node3.outputs['Color'], mix_rgb_node4.inputs['Color2'])

					mat.node_tree.links.new(mix_rgb_node4.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Base Color'])

					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.2
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 1.0

					#Normal
					mix_rgb_node3 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					mapping_node2 = mat.node_tree.nodes.new(type='ShaderNodeMapping')
					normal_map_node1 = mat.node_tree.nodes.new(type='ShaderNodeNormalMap')
					normal_map_node2 = mat.node_tree.nodes.new(type='ShaderNodeNormalMap')
					normal_map_node1.uv_map = "UVMap"
					normal_map_node2.uv_map = "UVMap"
					normal_map_node1.inputs['Strength'].default_value = 0.48
					normal_map_node2.inputs['Strength'].default_value = 0.4

					CrackMap_UScale_VScale_UOffset_VOffset = parameters_Data[parameters_Names.index("CrackMap_UScale_VScale_UOffset_VOffset")]

					mapping_node2.inputs[3].default_value[0] = CrackMap_UScale_VScale_UOffset_VOffset[0]*1.0
					mapping_node2.inputs[3].default_value[1] = CrackMap_UScale_VScale_UOffset_VOffset[1]*1.0

					mat.node_tree.links.new(uv_map_node1.outputs['UV'], mapping_node2.inputs[0])
					mat.node_tree.links.new(mapping_node1.outputs['Vector'], DetailMap_Normal_Sampler_tex.inputs['Vector'])
					mat.node_tree.links.new(mapping_node2.outputs['Vector'], Crack_Normal_Sampler_tex.inputs['Vector'])

					mat.node_tree.links.new(Crack_Normal_Sampler_tex.outputs['Color'], normal_map_node1.inputs['Color'])
					mat.node_tree.links.new(DetailMap_Normal_Sampler_tex.outputs['Color'], normal_map_node2.inputs['Color'])

					mat.node_tree.links.new(normal_map_node1.outputs['Normal'], mix_rgb_node3.inputs['Color1'])
					mat.node_tree.links.new(normal_map_node2.outputs['Normal'], mix_rgb_node3.inputs['Color2'])
					mat.node_tree.links.new(mix_rgb_node3.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Normal'])

				elif shader_type == "DriveableSurface_Lightmap":
					ColourMap_Sampler_tex = mat.node_tree.nodes['ColourMap_Sampler']
					DetailMap_Diffuse_Sampler_tex = mat.node_tree.nodes['DetailMap_Diffuse_Sampler']
					Crack_AO_Sampler_tex = mat.node_tree.nodes['Crack_AO_Sampler']
					DetailMap_Normal_Sampler_tex = mat.node_tree.nodes['DetailMap_Normal_Sampler']
					Crack_Normal_Sampler_tex = mat.node_tree.nodes['Crack_Normal_Sampler']

					DetailMapUvScale = parameters_Data[parameters_Names.index("DetailMapUvScale")]
					DiffuseA = parameters_Data[parameters_Names.index("DiffuseA")]
					DiffuseB = parameters_Data[parameters_Names.index("DiffuseB")]

					mix_rgb_node1 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					uv_map_node1 = mat.node_tree.nodes.new(type='ShaderNodeUVMap')
					mapping_node1 = mat.node_tree.nodes.new(type='ShaderNodeMapping')

					mix_rgb_node1.blend_type = "MIX"
					uv_map_node1.uv_map = "UVMap"

					mapping_node1.inputs[3].default_value[0] = DetailMapUvScale[0]*10.0
					mapping_node1.inputs[3].default_value[1] = DetailMapUvScale[1]*100.0

					mat.node_tree.links.new(uv_map_node1.outputs['UV'], mapping_node1.inputs[0])
					mat.node_tree.links.new(mapping_node1.outputs['Vector'], DetailMap_Diffuse_Sampler_tex.inputs['Vector'])

					mat.node_tree.links.new(ColourMap_Sampler_tex.outputs['Alpha'], mix_rgb_node1.inputs['Fac'])
					mat.node_tree.links.new(DetailMap_Diffuse_Sampler_tex.outputs['Color'], mix_rgb_node1.inputs['Color1'])
					mat.node_tree.links.new(ColourMap_Sampler_tex.outputs['Color'], mix_rgb_node1.inputs['Color2'])

					mat.node_tree.links.new(mix_rgb_node1.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Base Color'])

					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.2
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 1.0

					#Normal
					mix_rgb_node3 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					uv_map_node2 = mat.node_tree.nodes.new(type='ShaderNodeUVMap')
					mapping_node2 = mat.node_tree.nodes.new(type='ShaderNodeMapping')

					CrackMap_UScale_VScale_UOffset_VOffset = parameters_Data[parameters_Names.index("CrackMap_UScale_VScale_UOffset_VOffset")]

					uv_map_node2.uv_map = "UVMap"

					mapping_node2.inputs[3].default_value[0] = CrackMap_UScale_VScale_UOffset_VOffset[0]*1.0
					mapping_node2.inputs[3].default_value[1] = CrackMap_UScale_VScale_UOffset_VOffset[1]*1.0

					mat.node_tree.links.new(uv_map_node2.outputs['UV'], mapping_node2.inputs[0])
					mat.node_tree.links.new(mapping_node2.outputs['Vector'], Crack_Normal_Sampler_tex.inputs['Vector'])

					mat.node_tree.links.new(mapping_node1.outputs['Vector'], DetailMap_Normal_Sampler_tex.inputs['Vector'])

					mat.node_tree.links.new(Crack_Normal_Sampler_tex.outputs['Color'], mix_rgb_node3.inputs['Color1'])
					mat.node_tree.links.new(DetailMap_Normal_Sampler_tex.outputs['Color'], mix_rgb_node3.inputs['Color2'])
					mat.node_tree.links.new(mix_rgb_node3.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Normal'])

				elif shader_type == "DriveableSurface_RetroreflectivePaint_CarPark":
					ColourMap_Sampler_tex = mat.node_tree.nodes['ColourMap_Sampler']
					DetailMap_Diffuse_Sampler_tex = mat.node_tree.nodes['DetailMap_Diffuse_Sampler']
					Crack_AO_Sampler_tex = mat.node_tree.nodes['Crack_AO_Sampler']
					DetailMap_Normal_Sampler_tex = mat.node_tree.nodes['DetailMap_Normal_Sampler']
					Crack_Normal_Sampler_tex = mat.node_tree.nodes['Crack_Normal_Sampler']
					OverlayA_Sampler_tex = mat.node_tree.nodes['OverlayA_Sampler']
					OverlayB_Sampler_tex = mat.node_tree.nodes['OverlayB_Sampler']
					Line_Diffuse_Sampler_tex = mat.node_tree.nodes['Line_Diffuse_Sampler']

					DetailMapUvScale = parameters_Data[parameters_Names.index("DetailMapUvScale")]
					DiffuseA = parameters_Data[parameters_Names.index("DiffuseA")]
					DiffuseB = parameters_Data[parameters_Names.index("DiffuseB")]
					OverlayA_Diffuse = parameters_Data[parameters_Names.index("OverlayA_Diffuse")]
					OverlayB_Diffuse = parameters_Data[parameters_Names.index("OverlayB_Diffuse")]
					Line_Diffuse = parameters_Data[parameters_Names.index("Line_Diffuse")]

					mix_rgb_node1 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					mix_rgb_node2 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					mix_rgb_node3 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					mix_rgb_node4 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					uv_map_node1 = mat.node_tree.nodes.new(type='ShaderNodeUVMap')
					uv_map_node2 = mat.node_tree.nodes.new(type='ShaderNodeUVMap')
					mapping_node1 = mat.node_tree.nodes.new(type='ShaderNodeMapping')

					mix_rgb_node1.blend_type = "OVERLAY"
					mix_rgb_node2.blend_type = "OVERLAY"
					mix_rgb_node3.blend_type = "OVERLAY"
					mix_rgb_node4.blend_type = "MIX"
					uv_map_node1.uv_map = "UVMap"
					uv_map_node2.uv_map = "UV3Map"
					mix_rgb_node2.inputs['Color2'].default_value = OverlayB_Diffuse
					mix_rgb_node3.inputs['Color2'].default_value = Line_Diffuse

					mapping_node1.inputs[3].default_value[0] = DetailMapUvScale[0]*1.0
					mapping_node1.inputs[3].default_value[1] = DetailMapUvScale[1]*1.0

					mat.node_tree.links.new(uv_map_node1.outputs['UV'], mapping_node1.inputs[0])
					mat.node_tree.links.new(mapping_node1.outputs['Vector'], DetailMap_Diffuse_Sampler_tex.inputs['Vector'])

					mat.node_tree.links.new(OverlayA_Sampler_tex.outputs['Color'], mix_rgb_node1.inputs['Fac'])
					mat.node_tree.links.new(DetailMap_Diffuse_Sampler_tex.outputs['Color'], mix_rgb_node1.inputs['Color1'])
					mat.node_tree.links.new(ColourMap_Sampler_tex.outputs['Color'], mix_rgb_node1.inputs['Color2'])

					mat.node_tree.links.new(OverlayB_Sampler_tex.outputs['Color'], mix_rgb_node2.inputs['Fac'])
					mat.node_tree.links.new(mix_rgb_node1.outputs['Color'], mix_rgb_node2.inputs['Color1'])

					mat.node_tree.links.new(uv_map_node2.outputs['UV'], Line_Diffuse_Sampler_tex.inputs['Vector'])
					mat.node_tree.links.new(Line_Diffuse_Sampler_tex.outputs['Color'], mix_rgb_node3.inputs['Color1'])
					mat.node_tree.links.new(Line_Diffuse_Sampler_tex.outputs['Alpha'], mix_rgb_node3.inputs['Fac'])

					mat.node_tree.links.new(Line_Diffuse_Sampler_tex.outputs['Alpha'], mix_rgb_node4.inputs['Fac'])
					mat.node_tree.links.new(mix_rgb_node2.outputs['Color'], mix_rgb_node4.inputs['Color1'])
					mat.node_tree.links.new(mix_rgb_node3.outputs['Color'], mix_rgb_node4.inputs['Color2'])

					mat.node_tree.links.new(mix_rgb_node4.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Base Color'])

					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.2
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 1.0

					#Normal
					mix_rgb_node3 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					mapping_node2 = mat.node_tree.nodes.new(type='ShaderNodeMapping')
					normal_map_node1 = mat.node_tree.nodes.new(type='ShaderNodeNormalMap')
					normal_map_node2 = mat.node_tree.nodes.new(type='ShaderNodeNormalMap')
					normal_map_node1.uv_map = "UVMap"
					normal_map_node2.uv_map = "UVMap"
					normal_map_node1.inputs['Strength'].default_value = 0.48
					normal_map_node2.inputs['Strength'].default_value = 0.4

					CrackMap_UScale_VScale_UOffset_VOffset = parameters_Data[parameters_Names.index("CrackMap_UScale_VScale_UOffset_VOffset")]

					mapping_node2.inputs[3].default_value[0] = CrackMap_UScale_VScale_UOffset_VOffset[0]*1.0
					mapping_node2.inputs[3].default_value[1] = CrackMap_UScale_VScale_UOffset_VOffset[1]*1.0

					mat.node_tree.links.new(uv_map_node1.outputs['UV'], mapping_node2.inputs[0])
					mat.node_tree.links.new(mapping_node1.outputs['Vector'], DetailMap_Normal_Sampler_tex.inputs['Vector'])
					mat.node_tree.links.new(mapping_node2.outputs['Vector'], Crack_Normal_Sampler_tex.inputs['Vector'])

					mat.node_tree.links.new(Crack_Normal_Sampler_tex.outputs['Color'], normal_map_node1.inputs['Color'])
					mat.node_tree.links.new(DetailMap_Normal_Sampler_tex.outputs['Color'], normal_map_node2.inputs['Color'])

					mat.node_tree.links.new(normal_map_node1.outputs['Normal'], mix_rgb_node3.inputs['Color1'])
					mat.node_tree.links.new(normal_map_node2.outputs['Normal'], mix_rgb_node3.inputs['Color2'])
					mat.node_tree.links.new(mix_rgb_node3.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Normal'])

				elif shader_type == "DriveableSurface_RetroreflectivePaint_LineFade":
					ColourMap_Sampler_tex = mat.node_tree.nodes['ColourMap_Sampler']
					DetailMap_Diffuse_Sampler_tex = mat.node_tree.nodes['DetailMap_Diffuse_Sampler']
					Crack_AO_Sampler_tex = mat.node_tree.nodes['Crack_AO_Sampler']
					DetailMap_Normal_Sampler_tex = mat.node_tree.nodes['DetailMap_Normal_Sampler']
					Crack_Normal_Sampler_tex = mat.node_tree.nodes['Crack_Normal_Sampler']
					OverlayA_Sampler_tex = mat.node_tree.nodes['OverlayA_Sampler']
					OverlayB_Sampler_tex = mat.node_tree.nodes['OverlayB_Sampler']
					Line_Diffuse_Sampler_tex = mat.node_tree.nodes['Line_Diffuse_Sampler']

					DetailMapUvScale = parameters_Data[parameters_Names.index("DetailMapUvScale")]
					DiffuseA = parameters_Data[parameters_Names.index("DiffuseA")]
					DiffuseB = parameters_Data[parameters_Names.index("DiffuseB")]
					OverlayA_Diffuse = parameters_Data[parameters_Names.index("OverlayA_Diffuse")]
					OverlayB_Diffuse = parameters_Data[parameters_Names.index("OverlayB_Diffuse")]
					Line_Diffuse = parameters_Data[parameters_Names.index("Line_Diffuse")]

					mix_rgb_node1 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					mix_rgb_node2 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					mix_rgb_node3 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					mix_rgb_node4 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					uv_map_node1 = mat.node_tree.nodes.new(type='ShaderNodeUVMap')
					uv_map_node2 = mat.node_tree.nodes.new(type='ShaderNodeUVMap')
					mapping_node1 = mat.node_tree.nodes.new(type='ShaderNodeMapping')

					mix_rgb_node1.blend_type = "OVERLAY"
					mix_rgb_node2.blend_type = "OVERLAY"
					mix_rgb_node3.blend_type = "OVERLAY"
					mix_rgb_node4.blend_type = "MIX"
					uv_map_node1.uv_map = "UVMap"
					uv_map_node2.uv_map = "UV3Map"
					mix_rgb_node2.inputs['Color2'].default_value = OverlayB_Diffuse
					mix_rgb_node3.inputs['Color2'].default_value = Line_Diffuse

					mapping_node1.inputs[3].default_value[0] = DetailMapUvScale[0]*10.0
					mapping_node1.inputs[3].default_value[1] = DetailMapUvScale[1]*100.0

					mat.node_tree.links.new(uv_map_node1.outputs['UV'], mapping_node1.inputs[0])
					mat.node_tree.links.new(mapping_node1.outputs['Vector'], DetailMap_Diffuse_Sampler_tex.inputs['Vector'])

					mat.node_tree.links.new(OverlayA_Sampler_tex.outputs['Color'], mix_rgb_node1.inputs['Fac'])
					mat.node_tree.links.new(DetailMap_Diffuse_Sampler_tex.outputs['Color'], mix_rgb_node1.inputs['Color1'])
					mat.node_tree.links.new(ColourMap_Sampler_tex.outputs['Color'], mix_rgb_node1.inputs['Color2'])

					mat.node_tree.links.new(OverlayB_Sampler_tex.outputs['Color'], mix_rgb_node2.inputs['Fac'])
					mat.node_tree.links.new(mix_rgb_node1.outputs['Color'], mix_rgb_node2.inputs['Color1'])

					mat.node_tree.links.new(uv_map_node2.outputs['UV'], Line_Diffuse_Sampler_tex.inputs['Vector'])
					mat.node_tree.links.new(Line_Diffuse_Sampler_tex.outputs['Color'], mix_rgb_node3.inputs['Color1'])
					mat.node_tree.links.new(Line_Diffuse_Sampler_tex.outputs['Alpha'], mix_rgb_node3.inputs['Fac'])

					mat.node_tree.links.new(Line_Diffuse_Sampler_tex.outputs['Alpha'], mix_rgb_node4.inputs['Fac'])
					mat.node_tree.links.new(mix_rgb_node2.outputs['Color'], mix_rgb_node4.inputs['Color1'])
					mat.node_tree.links.new(mix_rgb_node3.outputs['Color'], mix_rgb_node4.inputs['Color2'])

					mat.node_tree.links.new(mix_rgb_node4.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Base Color'])

					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.2
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 1.0

					#Normal
					mix_rgb_node3 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					mapping_node2 = mat.node_tree.nodes.new(type='ShaderNodeMapping')
					normal_map_node1 = mat.node_tree.nodes.new(type='ShaderNodeNormalMap')
					normal_map_node2 = mat.node_tree.nodes.new(type='ShaderNodeNormalMap')
					normal_map_node1.uv_map = "UVMap"
					normal_map_node2.uv_map = "UVMap"
					normal_map_node1.inputs['Strength'].default_value = 0.48
					normal_map_node2.inputs['Strength'].default_value = 0.4

					CrackMap_UScale_VScale_UOffset_VOffset = parameters_Data[parameters_Names.index("CrackMap_UScale_VScale_UOffset_VOffset")]

					mapping_node2.inputs[3].default_value[0] = CrackMap_UScale_VScale_UOffset_VOffset[0]*1.0
					mapping_node2.inputs[3].default_value[1] = CrackMap_UScale_VScale_UOffset_VOffset[1]*1.0

					mat.node_tree.links.new(uv_map_node1.outputs['UV'], mapping_node2.inputs[0])
					mat.node_tree.links.new(mapping_node1.outputs['Vector'], DetailMap_Normal_Sampler_tex.inputs['Vector'])
					mat.node_tree.links.new(mapping_node2.outputs['Vector'], Crack_Normal_Sampler_tex.inputs['Vector'])

					mat.node_tree.links.new(Crack_Normal_Sampler_tex.outputs['Color'], normal_map_node1.inputs['Color'])
					mat.node_tree.links.new(DetailMap_Normal_Sampler_tex.outputs['Color'], normal_map_node2.inputs['Color'])

					mat.node_tree.links.new(normal_map_node1.outputs['Normal'], mix_rgb_node3.inputs['Color1'])
					mat.node_tree.links.new(normal_map_node2.outputs['Normal'], mix_rgb_node3.inputs['Color2'])
					mat.node_tree.links.new(mix_rgb_node3.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Normal'])

				elif shader_type == "DriveableSurface_RetroreflectivePaint_LineFade_Rotated_UV":
					ColourMap_Sampler_tex = mat.node_tree.nodes['ColourMap_Sampler']
					DetailMap_Diffuse_Sampler_tex = mat.node_tree.nodes['DetailMap_Diffuse_Sampler']
					Crack_AO_Sampler_tex = mat.node_tree.nodes['Crack_AO_Sampler']
					DetailMap_Normal_Sampler_tex = mat.node_tree.nodes['DetailMap_Normal_Sampler']
					Crack_Normal_Sampler_tex = mat.node_tree.nodes['Crack_Normal_Sampler']
					OverlayA_Sampler_tex = mat.node_tree.nodes['OverlayA_Sampler']
					OverlayB_Sampler_tex = mat.node_tree.nodes['OverlayB_Sampler']
					Line_Diffuse_Sampler_tex = mat.node_tree.nodes['Line_Diffuse_Sampler']

					DetailMapUvScale = parameters_Data[parameters_Names.index("DetailMapUvScale")]
					DiffuseA = parameters_Data[parameters_Names.index("DiffuseA")]
					DiffuseB = parameters_Data[parameters_Names.index("DiffuseB")]
					OverlayA_Diffuse = parameters_Data[parameters_Names.index("OverlayA_Diffuse")]
					OverlayB_Diffuse = parameters_Data[parameters_Names.index("OverlayB_Diffuse")]
					Line_Diffuse = parameters_Data[parameters_Names.index("Line_Diffuse")]

					mix_rgb_node1 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					mix_rgb_node2 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					mix_rgb_node3 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					mix_rgb_node4 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					uv_map_node1 = mat.node_tree.nodes.new(type='ShaderNodeUVMap')
					uv_map_node2 = mat.node_tree.nodes.new(type='ShaderNodeUVMap')
					mapping_node1 = mat.node_tree.nodes.new(type='ShaderNodeMapping')
					mapping_node2 = mat.node_tree.nodes.new(type='ShaderNodeMapping')

					mix_rgb_node1.blend_type = "OVERLAY"
					mix_rgb_node2.blend_type = "OVERLAY"
					mix_rgb_node3.blend_type = "OVERLAY"
					mix_rgb_node4.blend_type = "MIX"
					uv_map_node1.uv_map = "UVMap"
					uv_map_node2.uv_map = "UV3Map"
					mix_rgb_node2.inputs['Color2'].default_value = OverlayB_Diffuse
					mix_rgb_node3.inputs['Color2'].default_value = Line_Diffuse

					mapping_node1.inputs[3].default_value[0] = DetailMapUvScale[0]*10.0
					mapping_node1.inputs[3].default_value[1] = DetailMapUvScale[1]*100.0

					mapping_node2.inputs[2].default_value[2] = 1.570796326

					mat.node_tree.links.new(uv_map_node1.outputs['UV'], mapping_node1.inputs[0])
					mat.node_tree.links.new(mapping_node1.outputs['Vector'], DetailMap_Diffuse_Sampler_tex.inputs['Vector'])

					mat.node_tree.links.new(OverlayA_Sampler_tex.outputs['Color'], mix_rgb_node1.inputs['Fac'])
					mat.node_tree.links.new(DetailMap_Diffuse_Sampler_tex.outputs['Color'], mix_rgb_node1.inputs['Color1'])
					mat.node_tree.links.new(ColourMap_Sampler_tex.outputs['Color'], mix_rgb_node1.inputs['Color2'])

					mat.node_tree.links.new(OverlayB_Sampler_tex.outputs['Color'], mix_rgb_node2.inputs['Fac'])
					mat.node_tree.links.new(mix_rgb_node1.outputs['Color'], mix_rgb_node2.inputs['Color1'])

					mat.node_tree.links.new(uv_map_node2.outputs['UV'], mapping_node2.inputs[0])
					mat.node_tree.links.new(mapping_node2.outputs['Vector'], Line_Diffuse_Sampler_tex.inputs['Vector'])
					mat.node_tree.links.new(Line_Diffuse_Sampler_tex.outputs['Color'], mix_rgb_node3.inputs['Color1'])
					mat.node_tree.links.new(Line_Diffuse_Sampler_tex.outputs['Alpha'], mix_rgb_node3.inputs['Fac'])

					mat.node_tree.links.new(Line_Diffuse_Sampler_tex.outputs['Alpha'], mix_rgb_node4.inputs['Fac'])
					mat.node_tree.links.new(mix_rgb_node2.outputs['Color'], mix_rgb_node4.inputs['Color1'])
					mat.node_tree.links.new(mix_rgb_node3.outputs['Color'], mix_rgb_node4.inputs['Color2'])

					mat.node_tree.links.new(mix_rgb_node4.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Base Color'])

					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.2
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 1.0

					#Normal
					mix_rgb_node3 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					mapping_node2 = mat.node_tree.nodes.new(type='ShaderNodeMapping')
					normal_map_node1 = mat.node_tree.nodes.new(type='ShaderNodeNormalMap')
					normal_map_node2 = mat.node_tree.nodes.new(type='ShaderNodeNormalMap')
					normal_map_node1.uv_map = "UVMap"
					normal_map_node2.uv_map = "UVMap"
					normal_map_node1.inputs['Strength'].default_value = 0.48
					normal_map_node2.inputs['Strength'].default_value = 0.4

					CrackMap_UScale_VScale_UOffset_VOffset = parameters_Data[parameters_Names.index("CrackMap_UScale_VScale_UOffset_VOffset")]

					mapping_node2.inputs[3].default_value[0] = CrackMap_UScale_VScale_UOffset_VOffset[0]*1.0
					mapping_node2.inputs[3].default_value[1] = CrackMap_UScale_VScale_UOffset_VOffset[1]*1.0

					mat.node_tree.links.new(uv_map_node1.outputs['UV'], mapping_node2.inputs[0])
					mat.node_tree.links.new(mapping_node1.outputs['Vector'], DetailMap_Normal_Sampler_tex.inputs['Vector'])
					mat.node_tree.links.new(mapping_node2.outputs['Vector'], Crack_Normal_Sampler_tex.inputs['Vector'])

					mat.node_tree.links.new(Crack_Normal_Sampler_tex.outputs['Color'], normal_map_node1.inputs['Color'])
					mat.node_tree.links.new(DetailMap_Normal_Sampler_tex.outputs['Color'], normal_map_node2.inputs['Color'])

					mat.node_tree.links.new(normal_map_node1.outputs['Normal'], mix_rgb_node3.inputs['Color1'])
					mat.node_tree.links.new(normal_map_node2.outputs['Normal'], mix_rgb_node3.inputs['Color2'])
					mat.node_tree.links.new(mix_rgb_node3.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Normal'])

				elif shader_type == "DriveableSurface_RetroreflectivePaint_LineFade_Rotated_UV_02":
					ColourMap_Sampler_tex = mat.node_tree.nodes['ColourMap_Sampler']
					DetailMap_Diffuse_Sampler_tex = mat.node_tree.nodes['DetailMap_Diffuse_Sampler']
					Crack_AO_Sampler_tex = mat.node_tree.nodes['Crack_AO_Sampler']
					DetailMap_Normal_Sampler_tex = mat.node_tree.nodes['DetailMap_Normal_Sampler']
					Crack_Normal_Sampler_tex = mat.node_tree.nodes['Crack_Normal_Sampler']
					OverlayA_Sampler_tex = mat.node_tree.nodes['OverlayA_Sampler']
					OverlayB_Sampler_tex = mat.node_tree.nodes['OverlayB_Sampler']
					Line_Diffuse_Sampler_tex = mat.node_tree.nodes['Line_Diffuse_Sampler']

					DetailMapUvScale = parameters_Data[parameters_Names.index("DetailMapUvScale")]
					DiffuseA = parameters_Data[parameters_Names.index("DiffuseA")]
					DiffuseB = parameters_Data[parameters_Names.index("DiffuseB")]
					OverlayA_Diffuse = parameters_Data[parameters_Names.index("OverlayA_Diffuse")]
					OverlayB_Diffuse = parameters_Data[parameters_Names.index("OverlayB_Diffuse")]
					Line_Diffuse = parameters_Data[parameters_Names.index("Line_Diffuse")]

					mix_rgb_node1 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					mix_rgb_node2 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					mix_rgb_node3 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					mix_rgb_node4 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					uv_map_node1 = mat.node_tree.nodes.new(type='ShaderNodeUVMap')
					uv_map_node2 = mat.node_tree.nodes.new(type='ShaderNodeUVMap')
					mapping_node1 = mat.node_tree.nodes.new(type='ShaderNodeMapping')
					mapping_node2 = mat.node_tree.nodes.new(type='ShaderNodeMapping')

					mix_rgb_node1.blend_type = "OVERLAY"
					mix_rgb_node2.blend_type = "OVERLAY"
					mix_rgb_node3.blend_type = "OVERLAY"
					mix_rgb_node4.blend_type = "MIX"
					uv_map_node1.uv_map = "UVMap"
					uv_map_node2.uv_map = "UV3Map"
					mix_rgb_node2.inputs['Color2'].default_value = OverlayB_Diffuse
					mix_rgb_node3.inputs['Color2'].default_value = Line_Diffuse

					mapping_node1.inputs[3].default_value[0] = DetailMapUvScale[0]*10.0
					mapping_node1.inputs[3].default_value[1] = DetailMapUvScale[1]*100.0

					mapping_node2.inputs[2].default_value[2] = 1.570796326

					mat.node_tree.links.new(uv_map_node1.outputs['UV'], mapping_node1.inputs[0])
					mat.node_tree.links.new(mapping_node1.outputs['Vector'], DetailMap_Diffuse_Sampler_tex.inputs['Vector'])

					mat.node_tree.links.new(OverlayA_Sampler_tex.outputs['Color'], mix_rgb_node1.inputs['Fac'])
					mat.node_tree.links.new(DetailMap_Diffuse_Sampler_tex.outputs['Color'], mix_rgb_node1.inputs['Color1'])
					mat.node_tree.links.new(ColourMap_Sampler_tex.outputs['Color'], mix_rgb_node1.inputs['Color2'])

					mat.node_tree.links.new(OverlayB_Sampler_tex.outputs['Color'], mix_rgb_node2.inputs['Fac'])
					mat.node_tree.links.new(mix_rgb_node1.outputs['Color'], mix_rgb_node2.inputs['Color1'])

					mat.node_tree.links.new(uv_map_node2.outputs['UV'], mapping_node2.inputs[0])
					mat.node_tree.links.new(mapping_node2.outputs['Vector'], Line_Diffuse_Sampler_tex.inputs['Vector'])
					mat.node_tree.links.new(Line_Diffuse_Sampler_tex.outputs['Color'], mix_rgb_node3.inputs['Color1'])
					mat.node_tree.links.new(Line_Diffuse_Sampler_tex.outputs['Alpha'], mix_rgb_node3.inputs['Fac'])

					mat.node_tree.links.new(Line_Diffuse_Sampler_tex.outputs['Alpha'], mix_rgb_node4.inputs['Fac'])
					mat.node_tree.links.new(mix_rgb_node2.outputs['Color'], mix_rgb_node4.inputs['Color1'])
					mat.node_tree.links.new(mix_rgb_node3.outputs['Color'], mix_rgb_node4.inputs['Color2'])

					mat.node_tree.links.new(mix_rgb_node4.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Base Color'])

					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.2
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 1.0

					#Normal
					mix_rgb_node3 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					mapping_node4 = mat.node_tree.nodes.new(type='ShaderNodeMapping')
					normal_map_node1 = mat.node_tree.nodes.new(type='ShaderNodeNormalMap')
					normal_map_node2 = mat.node_tree.nodes.new(type='ShaderNodeNormalMap')
					normal_map_node1.uv_map = "UVMap"
					normal_map_node2.uv_map = "UVMap"
					normal_map_node1.inputs['Strength'].default_value = 0.48
					normal_map_node2.inputs['Strength'].default_value = 0.4

					CrackMap_UScale_VScale_UOffset_VOffset = parameters_Data[parameters_Names.index("CrackMap_UScale_VScale_UOffset_VOffset")]

					mapping_node4.inputs[3].default_value[0] = CrackMap_UScale_VScale_UOffset_VOffset[0]*1.0
					mapping_node4.inputs[3].default_value[1] = CrackMap_UScale_VScale_UOffset_VOffset[1]*1.0

					mat.node_tree.links.new(uv_map_node1.outputs['UV'], mapping_node4.inputs[0])
					mat.node_tree.links.new(mapping_node1.outputs['Vector'], DetailMap_Normal_Sampler_tex.inputs['Vector'])
					mat.node_tree.links.new(mapping_node4.outputs['Vector'], Crack_Normal_Sampler_tex.inputs['Vector'])

					mat.node_tree.links.new(Crack_Normal_Sampler_tex.outputs['Color'], normal_map_node1.inputs['Color'])
					mat.node_tree.links.new(DetailMap_Normal_Sampler_tex.outputs['Color'], normal_map_node2.inputs['Color'])

					mat.node_tree.links.new(normal_map_node1.outputs['Normal'], mix_rgb_node3.inputs['Color1'])
					mat.node_tree.links.new(normal_map_node2.outputs['Normal'], mix_rgb_node3.inputs['Color2'])
					mat.node_tree.links.new(mix_rgb_node3.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Normal'])

				elif shader_type == "DriveableSurface_RetroreflectivePaint_Lightmap":
					ColourMap_Sampler_tex = mat.node_tree.nodes['ColourMap_Sampler']
					DetailMap_Diffuse_Sampler_tex = mat.node_tree.nodes['DetailMap_Diffuse_Sampler']
					Crack_AO_Sampler_tex = mat.node_tree.nodes['Crack_AO_Sampler']
					DetailMap_Normal_Sampler_tex = mat.node_tree.nodes['DetailMap_Normal_Sampler']
					Crack_Normal_Sampler_tex = mat.node_tree.nodes['Crack_Normal_Sampler']
					Line_Diffuse_Sampler_tex = mat.node_tree.nodes['Line_Diffuse_Sampler']

					DetailMapUvScale = parameters_Data[parameters_Names.index("DetailMapUvScale")]
					DiffuseA = parameters_Data[parameters_Names.index("DiffuseA")]
					DiffuseB = parameters_Data[parameters_Names.index("DiffuseB")]
					Line_Diffuse = parameters_Data[parameters_Names.index("Line_Diffuse")]

					mix_rgb_node1 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					mix_rgb_node3 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					mix_rgb_node4 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					uv_map_node1 = mat.node_tree.nodes.new(type='ShaderNodeUVMap')
					uv_map_node2 = mat.node_tree.nodes.new(type='ShaderNodeUVMap')
					mapping_node1 = mat.node_tree.nodes.new(type='ShaderNodeMapping')

					mix_rgb_node1.blend_type = "MIX"
					mix_rgb_node3.blend_type = "OVERLAY"
					mix_rgb_node4.blend_type = "MIX"
					uv_map_node1.uv_map = "UVMap"
					uv_map_node2.uv_map = "UV3Map"
					mix_rgb_node3.inputs['Color2'].default_value = Line_Diffuse

					mapping_node1.inputs[3].default_value[0] = DetailMapUvScale[0]*10.0
					mapping_node1.inputs[3].default_value[1] = DetailMapUvScale[1]*100.0

					mat.node_tree.links.new(uv_map_node1.outputs['UV'], mapping_node1.inputs[0])
					mat.node_tree.links.new(mapping_node1.outputs['Vector'], DetailMap_Diffuse_Sampler_tex.inputs['Vector'])

					mat.node_tree.links.new(ColourMap_Sampler_tex.outputs['Alpha'], mix_rgb_node1.inputs['Fac'])
					mat.node_tree.links.new(DetailMap_Diffuse_Sampler_tex.outputs['Color'], mix_rgb_node1.inputs['Color1'])
					mat.node_tree.links.new(ColourMap_Sampler_tex.outputs['Color'], mix_rgb_node1.inputs['Color2'])

					mat.node_tree.links.new(uv_map_node2.outputs['UV'], Line_Diffuse_Sampler_tex.inputs['Vector'])
					mat.node_tree.links.new(Line_Diffuse_Sampler_tex.outputs['Color'], mix_rgb_node3.inputs['Color1'])
					mat.node_tree.links.new(Line_Diffuse_Sampler_tex.outputs['Alpha'], mix_rgb_node3.inputs['Fac'])

					mat.node_tree.links.new(Line_Diffuse_Sampler_tex.outputs['Alpha'], mix_rgb_node4.inputs['Fac'])
					mat.node_tree.links.new(mix_rgb_node1.outputs['Color'], mix_rgb_node4.inputs['Color1'])
					mat.node_tree.links.new(mix_rgb_node3.outputs['Color'], mix_rgb_node4.inputs['Color2'])

					mat.node_tree.links.new(mix_rgb_node4.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Base Color'])

					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.2
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 1.0

					#Normal
					mix_rgb_node5 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					uv_map_node3 = mat.node_tree.nodes.new(type='ShaderNodeUVMap')
					mapping_node2 = mat.node_tree.nodes.new(type='ShaderNodeMapping')

					CrackMap_UScale_VScale_UOffset_VOffset = parameters_Data[parameters_Names.index("CrackMap_UScale_VScale_UOffset_VOffset")]

					uv_map_node3.uv_map = "UVMap"

					mapping_node2.inputs[3].default_value[0] = CrackMap_UScale_VScale_UOffset_VOffset[0]*1.0
					mapping_node2.inputs[3].default_value[1] = CrackMap_UScale_VScale_UOffset_VOffset[1]*1.0

					mat.node_tree.links.new(uv_map_node3.outputs['UV'], mapping_node2.inputs[0])
					mat.node_tree.links.new(mapping_node2.outputs['Vector'], Crack_Normal_Sampler_tex.inputs['Vector'])

					mat.node_tree.links.new(mapping_node1.outputs['Vector'], DetailMap_Normal_Sampler_tex.inputs['Vector'])

					mat.node_tree.links.new(Crack_Normal_Sampler_tex.outputs['Color'], mix_rgb_node5.inputs['Color1'])
					mat.node_tree.links.new(DetailMap_Normal_Sampler_tex.outputs['Color'], mix_rgb_node5.inputs['Color2'])
					mat.node_tree.links.new(mix_rgb_node5.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Normal'])

				elif shader_type == "DriveableSurface_RetroreflectivePaint_Lightmap_Car_Select":
					ColourMap_Sampler_tex = mat.node_tree.nodes['ColourMap_Sampler']
					DetailMap_Diffuse_Sampler_tex = mat.node_tree.nodes['DetailMap_Diffuse_Sampler']
					Crack_AO_Sampler_tex = mat.node_tree.nodes['Crack_AO_Sampler']
					DetailMap_Normal_Sampler_tex = mat.node_tree.nodes['DetailMap_Normal_Sampler']
					Crack_Normal_Sampler_tex = mat.node_tree.nodes['Crack_Normal_Sampler']
					Line_Diffuse_Sampler_tex = mat.node_tree.nodes['Line_Diffuse_Sampler']

					DetailMapUvScale = parameters_Data[parameters_Names.index("DetailMapUvScale")]
					DiffuseA = parameters_Data[parameters_Names.index("DiffuseA")]
					DiffuseB = parameters_Data[parameters_Names.index("DiffuseB")]
					Line_Diffuse = parameters_Data[parameters_Names.index("Line_Diffuse")]

					mix_rgb_node1 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					mix_rgb_node3 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					mix_rgb_node4 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					uv_map_node1 = mat.node_tree.nodes.new(type='ShaderNodeUVMap')
					uv_map_node2 = mat.node_tree.nodes.new(type='ShaderNodeUVMap')
					mapping_node1 = mat.node_tree.nodes.new(type='ShaderNodeMapping')

					mix_rgb_node1.blend_type = "MIX"
					mix_rgb_node3.blend_type = "OVERLAY"
					mix_rgb_node4.blend_type = "MIX"
					uv_map_node1.uv_map = "UVMap"
					uv_map_node2.uv_map = "UV3Map"
					mix_rgb_node3.inputs['Color2'].default_value = Line_Diffuse

					mapping_node1.inputs[3].default_value[0] = DetailMapUvScale[0]*10.0
					mapping_node1.inputs[3].default_value[1] = DetailMapUvScale[1]*100.0

					mat.node_tree.links.new(uv_map_node1.outputs['UV'], mapping_node1.inputs[0])
					mat.node_tree.links.new(mapping_node1.outputs['Vector'], DetailMap_Diffuse_Sampler_tex.inputs['Vector'])

					mat.node_tree.links.new(ColourMap_Sampler_tex.outputs['Alpha'], mix_rgb_node1.inputs['Fac'])
					mat.node_tree.links.new(DetailMap_Diffuse_Sampler_tex.outputs['Color'], mix_rgb_node1.inputs['Color1'])
					mat.node_tree.links.new(ColourMap_Sampler_tex.outputs['Color'], mix_rgb_node1.inputs['Color2'])

					mat.node_tree.links.new(uv_map_node2.outputs['UV'], Line_Diffuse_Sampler_tex.inputs['Vector'])
					mat.node_tree.links.new(Line_Diffuse_Sampler_tex.outputs['Color'], mix_rgb_node3.inputs['Color1'])
					mat.node_tree.links.new(Line_Diffuse_Sampler_tex.outputs['Alpha'], mix_rgb_node3.inputs['Fac'])

					mat.node_tree.links.new(Line_Diffuse_Sampler_tex.outputs['Alpha'], mix_rgb_node4.inputs['Fac'])
					mat.node_tree.links.new(mix_rgb_node1.outputs['Color'], mix_rgb_node4.inputs['Color1'])
					mat.node_tree.links.new(mix_rgb_node3.outputs['Color'], mix_rgb_node4.inputs['Color2'])

					mat.node_tree.links.new(mix_rgb_node4.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Base Color'])

					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.2
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 1.0

					#Normal
					mix_rgb_node5 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					uv_map_node3 = mat.node_tree.nodes.new(type='ShaderNodeUVMap')
					mapping_node2 = mat.node_tree.nodes.new(type='ShaderNodeMapping')

					CrackMap_UScale_VScale_UOffset_VOffset = parameters_Data[parameters_Names.index("CrackMap_UScale_VScale_UOffset_VOffset")]

					uv_map_node3.uv_map = "UVMap"

					mapping_node2.inputs[3].default_value[0] = CrackMap_UScale_VScale_UOffset_VOffset[0]*1.0
					mapping_node2.inputs[3].default_value[1] = CrackMap_UScale_VScale_UOffset_VOffset[1]*1.0

					mat.node_tree.links.new(uv_map_node3.outputs['UV'], mapping_node2.inputs[0])
					mat.node_tree.links.new(mapping_node2.outputs['Vector'], Crack_Normal_Sampler_tex.inputs['Vector'])

					mat.node_tree.links.new(mapping_node1.outputs['Vector'], DetailMap_Normal_Sampler_tex.inputs['Vector'])

					mat.node_tree.links.new(Crack_Normal_Sampler_tex.outputs['Color'], mix_rgb_node5.inputs['Color1'])
					mat.node_tree.links.new(DetailMap_Normal_Sampler_tex.outputs['Color'], mix_rgb_node5.inputs['Color2'])
					mat.node_tree.links.new(mix_rgb_node5.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Normal'])

				elif shader_type == "DriveableSurface_RetroreflectivePaint_Lightmap_LineFade":
					ColourMap_Sampler_tex = mat.node_tree.nodes['ColourMap_Sampler']
					DetailMap_Diffuse_Sampler_tex = mat.node_tree.nodes['DetailMap_Diffuse_Sampler']
					Crack_AO_Sampler_tex = mat.node_tree.nodes['Crack_AO_Sampler']
					DetailMap_Normal_Sampler_tex = mat.node_tree.nodes['DetailMap_Normal_Sampler']
					Crack_Normal_Sampler_tex = mat.node_tree.nodes['Crack_Normal_Sampler']
					Line_Diffuse_Sampler_tex = mat.node_tree.nodes['Line_Diffuse_Sampler']

					DetailMapUvScale = parameters_Data[parameters_Names.index("DetailMapUvScale")]
					DiffuseA = parameters_Data[parameters_Names.index("DiffuseA")]
					DiffuseB = parameters_Data[parameters_Names.index("DiffuseB")]
					Line_Diffuse = parameters_Data[parameters_Names.index("Line_Diffuse")]

					mix_rgb_node1 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					mix_rgb_node3 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					mix_rgb_node4 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					uv_map_node1 = mat.node_tree.nodes.new(type='ShaderNodeUVMap')
					uv_map_node2 = mat.node_tree.nodes.new(type='ShaderNodeUVMap')
					mapping_node1 = mat.node_tree.nodes.new(type='ShaderNodeMapping')

					mix_rgb_node1.blend_type = "MIX"
					mix_rgb_node3.blend_type = "OVERLAY"
					mix_rgb_node4.blend_type = "MIX"
					uv_map_node1.uv_map = "UVMap"
					uv_map_node2.uv_map = "UV3Map"
					mix_rgb_node3.inputs['Color2'].default_value = Line_Diffuse

					mapping_node1.inputs[3].default_value[0] = DetailMapUvScale[0]*10.0
					mapping_node1.inputs[3].default_value[1] = DetailMapUvScale[1]*100.0

					mat.node_tree.links.new(uv_map_node1.outputs['UV'], mapping_node1.inputs[0])
					mat.node_tree.links.new(mapping_node1.outputs['Vector'], DetailMap_Diffuse_Sampler_tex.inputs['Vector'])

					mat.node_tree.links.new(ColourMap_Sampler_tex.outputs['Alpha'], mix_rgb_node1.inputs['Fac'])
					mat.node_tree.links.new(DetailMap_Diffuse_Sampler_tex.outputs['Color'], mix_rgb_node1.inputs['Color1'])
					mat.node_tree.links.new(ColourMap_Sampler_tex.outputs['Color'], mix_rgb_node1.inputs['Color2'])

					mat.node_tree.links.new(uv_map_node2.outputs['UV'], Line_Diffuse_Sampler_tex.inputs['Vector'])
					mat.node_tree.links.new(Line_Diffuse_Sampler_tex.outputs['Color'], mix_rgb_node3.inputs['Color1'])
					mat.node_tree.links.new(Line_Diffuse_Sampler_tex.outputs['Alpha'], mix_rgb_node3.inputs['Fac'])

					mat.node_tree.links.new(Line_Diffuse_Sampler_tex.outputs['Alpha'], mix_rgb_node4.inputs['Fac'])
					mat.node_tree.links.new(mix_rgb_node1.outputs['Color'], mix_rgb_node4.inputs['Color1'])
					mat.node_tree.links.new(mix_rgb_node3.outputs['Color'], mix_rgb_node4.inputs['Color2'])

					mat.node_tree.links.new(mix_rgb_node4.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Base Color'])

					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.2
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 1.0

					#Normal
					mix_rgb_node5 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					uv_map_node3 = mat.node_tree.nodes.new(type='ShaderNodeUVMap')
					mapping_node2 = mat.node_tree.nodes.new(type='ShaderNodeMapping')

					CrackMap_UScale_VScale_UOffset_VOffset = parameters_Data[parameters_Names.index("CrackMap_UScale_VScale_UOffset_VOffset")]

					uv_map_node3.uv_map = "UVMap"

					mapping_node2.inputs[3].default_value[0] = CrackMap_UScale_VScale_UOffset_VOffset[0]*1.0
					mapping_node2.inputs[3].default_value[1] = CrackMap_UScale_VScale_UOffset_VOffset[1]*1.0

					mat.node_tree.links.new(uv_map_node3.outputs['UV'], mapping_node2.inputs[0])
					mat.node_tree.links.new(mapping_node2.outputs['Vector'], Crack_Normal_Sampler_tex.inputs['Vector'])

					mat.node_tree.links.new(mapping_node1.outputs['Vector'], DetailMap_Normal_Sampler_tex.inputs['Vector'])

					mat.node_tree.links.new(Crack_Normal_Sampler_tex.outputs['Color'], mix_rgb_node5.inputs['Color1'])
					mat.node_tree.links.new(DetailMap_Normal_Sampler_tex.outputs['Color'], mix_rgb_node5.inputs['Color2'])
					mat.node_tree.links.new(mix_rgb_node5.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Normal'])

				elif shader_type == "DriveableSurface_RetroreflectivePaint_Lightmap_LineFade_rotatedUV_02":
					ColourMap_Sampler_tex = mat.node_tree.nodes['ColourMap_Sampler']
					DetailMap_Diffuse_Sampler_tex = mat.node_tree.nodes['DetailMap_Diffuse_Sampler']
					Crack_AO_Sampler_tex = mat.node_tree.nodes['Crack_AO_Sampler']
					DetailMap_Normal_Sampler_tex = mat.node_tree.nodes['DetailMap_Normal_Sampler']
					Crack_Normal_Sampler_tex = mat.node_tree.nodes['Crack_Normal_Sampler']
					Line_Diffuse_Sampler_tex = mat.node_tree.nodes['Line_Diffuse_Sampler']

					DetailMapUvScale = parameters_Data[parameters_Names.index("DetailMapUvScale")]
					DiffuseA = parameters_Data[parameters_Names.index("DiffuseA")]
					DiffuseB = parameters_Data[parameters_Names.index("DiffuseB")]
					Line_Diffuse = parameters_Data[parameters_Names.index("Line_Diffuse")]

					mix_rgb_node1 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					mix_rgb_node3 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					mix_rgb_node4 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					uv_map_node1 = mat.node_tree.nodes.new(type='ShaderNodeUVMap')
					uv_map_node2 = mat.node_tree.nodes.new(type='ShaderNodeUVMap')
					mapping_node1 = mat.node_tree.nodes.new(type='ShaderNodeMapping')
					mapping_node2 = mat.node_tree.nodes.new(type='ShaderNodeMapping')

					mix_rgb_node1.blend_type = "MIX"
					mix_rgb_node3.blend_type = "OVERLAY"
					mix_rgb_node4.blend_type = "MIX"
					uv_map_node1.uv_map = "UVMap"
					uv_map_node2.uv_map = "UV3Map"
					mix_rgb_node3.inputs['Color2'].default_value = Line_Diffuse

					mapping_node1.inputs[3].default_value[0] = DetailMapUvScale[0]*10.0
					mapping_node1.inputs[3].default_value[1] = DetailMapUvScale[1]*100.0

					mapping_node2.inputs[2].default_value[2] = 1.570796326

					mat.node_tree.links.new(uv_map_node1.outputs['UV'], mapping_node1.inputs[0])
					mat.node_tree.links.new(mapping_node1.outputs['Vector'], DetailMap_Diffuse_Sampler_tex.inputs['Vector'])

					mat.node_tree.links.new(ColourMap_Sampler_tex.outputs['Alpha'], mix_rgb_node1.inputs['Fac'])
					mat.node_tree.links.new(DetailMap_Diffuse_Sampler_tex.outputs['Color'], mix_rgb_node1.inputs['Color1'])
					mat.node_tree.links.new(ColourMap_Sampler_tex.outputs['Color'], mix_rgb_node1.inputs['Color2'])

					mat.node_tree.links.new(uv_map_node2.outputs['UV'], mapping_node2.inputs[0])
					mat.node_tree.links.new(mapping_node2.outputs['Vector'], Line_Diffuse_Sampler_tex.inputs['Vector'])
					mat.node_tree.links.new(Line_Diffuse_Sampler_tex.outputs['Color'], mix_rgb_node3.inputs['Color1'])
					mat.node_tree.links.new(Line_Diffuse_Sampler_tex.outputs['Alpha'], mix_rgb_node3.inputs['Fac'])

					mat.node_tree.links.new(Line_Diffuse_Sampler_tex.outputs['Alpha'], mix_rgb_node4.inputs['Fac'])
					mat.node_tree.links.new(mix_rgb_node1.outputs['Color'], mix_rgb_node4.inputs['Color1'])
					mat.node_tree.links.new(mix_rgb_node3.outputs['Color'], mix_rgb_node4.inputs['Color2'])

					mat.node_tree.links.new(mix_rgb_node4.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Base Color'])

					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.2
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 1.0

					#Normal
					mix_rgb_node5 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					uv_map_node3 = mat.node_tree.nodes.new(type='ShaderNodeUVMap')
					mapping_node3 = mat.node_tree.nodes.new(type='ShaderNodeMapping')

					CrackMap_UScale_VScale_UOffset_VOffset = parameters_Data[parameters_Names.index("CrackMap_UScale_VScale_UOffset_VOffset")]

					uv_map_node3.uv_map = "UVMap"

					mapping_node3.inputs[3].default_value[0] = CrackMap_UScale_VScale_UOffset_VOffset[0]*1.0
					mapping_node3.inputs[3].default_value[1] = CrackMap_UScale_VScale_UOffset_VOffset[1]*1.0

					mat.node_tree.links.new(uv_map_node3.outputs['UV'], mapping_node3.inputs[0])
					mat.node_tree.links.new(mapping_node3.outputs['Vector'], Crack_Normal_Sampler_tex.inputs['Vector'])

					mat.node_tree.links.new(mapping_node1.outputs['Vector'], DetailMap_Normal_Sampler_tex.inputs['Vector'])

					mat.node_tree.links.new(Crack_Normal_Sampler_tex.outputs['Color'], mix_rgb_node5.inputs['Color1'])
					mat.node_tree.links.new(DetailMap_Normal_Sampler_tex.outputs['Color'], mix_rgb_node5.inputs['Color2'])
					mat.node_tree.links.new(mix_rgb_node5.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Normal'])

				elif shader_type == "DriveableSurface_RetroreflectivePaint":
					ColourMap_Sampler_tex = mat.node_tree.nodes['ColourMap_Sampler']
					DetailMap_Diffuse_Sampler_tex = mat.node_tree.nodes['DetailMap_Diffuse_Sampler']
					Crack_AO_Sampler_tex = mat.node_tree.nodes['Crack_AO_Sampler']
					DetailMap_Normal_Sampler_tex = mat.node_tree.nodes['DetailMap_Normal_Sampler']
					Crack_Normal_Sampler_tex = mat.node_tree.nodes['Crack_Normal_Sampler']
					OverlayA_Sampler_tex = mat.node_tree.nodes['OverlayA_Sampler']
					OverlayB_Sampler_tex = mat.node_tree.nodes['OverlayB_Sampler']
					Line_Diffuse_Sampler_tex = mat.node_tree.nodes['Line_Diffuse_Sampler']

					DetailMapUvScale = parameters_Data[parameters_Names.index("DetailMapUvScale")]
					DiffuseA = parameters_Data[parameters_Names.index("DiffuseA")]
					DiffuseB = parameters_Data[parameters_Names.index("DiffuseB")]
					OverlayA_Diffuse = parameters_Data[parameters_Names.index("OverlayA_Diffuse")]
					OverlayB_Diffuse = parameters_Data[parameters_Names.index("OverlayB_Diffuse")]
					Line_Diffuse = parameters_Data[parameters_Names.index("Line_Diffuse")]

					mix_rgb_node1 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					mix_rgb_node2 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					mix_rgb_node3 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					mix_rgb_node4 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					uv_map_node1 = mat.node_tree.nodes.new(type='ShaderNodeUVMap')
					uv_map_node2 = mat.node_tree.nodes.new(type='ShaderNodeUVMap')
					mapping_node1 = mat.node_tree.nodes.new(type='ShaderNodeMapping')

					mix_rgb_node1.blend_type = "OVERLAY"
					mix_rgb_node2.blend_type = "OVERLAY"
					mix_rgb_node3.blend_type = "OVERLAY"
					mix_rgb_node4.blend_type = "MIX"
					uv_map_node1.uv_map = "UVMap"
					uv_map_node2.uv_map = "UV3Map"
					mix_rgb_node2.inputs['Color2'].default_value = OverlayB_Diffuse
					mix_rgb_node3.inputs['Color2'].default_value = Line_Diffuse

					mapping_node1.inputs[3].default_value[0] = DetailMapUvScale[0]*10.0
					mapping_node1.inputs[3].default_value[1] = DetailMapUvScale[1]*100.0

					mat.node_tree.links.new(uv_map_node1.outputs['UV'], mapping_node1.inputs[0])
					mat.node_tree.links.new(mapping_node1.outputs['Vector'], DetailMap_Diffuse_Sampler_tex.inputs['Vector'])

					mat.node_tree.links.new(OverlayA_Sampler_tex.outputs['Color'], mix_rgb_node1.inputs['Fac'])
					mat.node_tree.links.new(DetailMap_Diffuse_Sampler_tex.outputs['Color'], mix_rgb_node1.inputs['Color1'])
					mat.node_tree.links.new(ColourMap_Sampler_tex.outputs['Color'], mix_rgb_node1.inputs['Color2'])

					mat.node_tree.links.new(OverlayB_Sampler_tex.outputs['Color'], mix_rgb_node2.inputs['Fac'])
					mat.node_tree.links.new(mix_rgb_node1.outputs['Color'], mix_rgb_node2.inputs['Color1'])


					mat.node_tree.links.new(uv_map_node2.outputs['UV'], Line_Diffuse_Sampler_tex.inputs['Vector'])
					mat.node_tree.links.new(Line_Diffuse_Sampler_tex.outputs['Color'], mix_rgb_node3.inputs['Color1'])
					mat.node_tree.links.new(Line_Diffuse_Sampler_tex.outputs['Alpha'], mix_rgb_node3.inputs['Fac'])

					mat.node_tree.links.new(Line_Diffuse_Sampler_tex.outputs['Alpha'], mix_rgb_node4.inputs['Fac'])
					mat.node_tree.links.new(mix_rgb_node2.outputs['Color'], mix_rgb_node4.inputs['Color1'])
					mat.node_tree.links.new(mix_rgb_node3.outputs['Color'], mix_rgb_node4.inputs['Color2'])

					mat.node_tree.links.new(mix_rgb_node4.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Base Color'])

					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.2
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 1.0

					#Normal
					mix_rgb_node3 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					mapping_node2 = mat.node_tree.nodes.new(type='ShaderNodeMapping')
					normal_map_node1 = mat.node_tree.nodes.new(type='ShaderNodeNormalMap')
					normal_map_node2 = mat.node_tree.nodes.new(type='ShaderNodeNormalMap')
					normal_map_node1.uv_map = "UVMap"
					normal_map_node2.uv_map = "UVMap"
					normal_map_node1.inputs['Strength'].default_value = 0.48
					normal_map_node2.inputs['Strength'].default_value = 0.4

					CrackMap_UScale_VScale_UOffset_VOffset = parameters_Data[parameters_Names.index("CrackMap_UScale_VScale_UOffset_VOffset")]

					mapping_node2.inputs[3].default_value[0] = CrackMap_UScale_VScale_UOffset_VOffset[0]*1.0
					mapping_node2.inputs[3].default_value[1] = CrackMap_UScale_VScale_UOffset_VOffset[1]*1.0

					mat.node_tree.links.new(uv_map_node1.outputs['UV'], mapping_node2.inputs[0])
					mat.node_tree.links.new(mapping_node1.outputs['Vector'], DetailMap_Normal_Sampler_tex.inputs['Vector'])
					mat.node_tree.links.new(mapping_node2.outputs['Vector'], Crack_Normal_Sampler_tex.inputs['Vector'])

					mat.node_tree.links.new(Crack_Normal_Sampler_tex.outputs['Color'], normal_map_node1.inputs['Color'])
					mat.node_tree.links.new(DetailMap_Normal_Sampler_tex.outputs['Color'], normal_map_node2.inputs['Color'])

					mat.node_tree.links.new(normal_map_node1.outputs['Normal'], mix_rgb_node3.inputs['Color1'])
					mat.node_tree.links.new(normal_map_node2.outputs['Normal'], mix_rgb_node3.inputs['Color2'])
					mat.node_tree.links.new(mix_rgb_node3.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Normal'])

				elif shader_type == "Fence_GreyScale_Singlesided":
					DiffuseTextureSampler_tex = mat.node_tree.nodes['DiffuseTextureSampler']

					mat.node_tree.links.new(DiffuseTextureSampler_tex.outputs['Alpha'], mat.node_tree.nodes[mMaterialId].inputs['Alpha'])

					mat.blend_method = 'BLEND'
					mat.shadow_method = 'HASHED'

					mat.use_backface_culling = True

					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 1.0
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 0.6

				elif shader_type == "Fence_GreyScale_Doublesided":
					DiffuseTextureSampler_tex = mat.node_tree.nodes['DiffuseTextureSampler']

					mat.node_tree.links.new(DiffuseTextureSampler_tex.outputs['Alpha'], mat.node_tree.nodes[mMaterialId].inputs['Alpha'])

					mat.blend_method = 'BLEND'
					mat.shadow_method = 'HASHED'

					mat.use_backface_culling = False

					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 1.0
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 0.6

				elif shader_type == "Flag_Opaque_Doublesided":
					mat.use_backface_culling = False

					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.0
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 0.3

				elif shader_type == "Flag_VerticalBanner_Opaque_Doublesided":
					mat.use_backface_culling = False

					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.0
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 0.3

				elif shader_type == "Foliage_1Bit_Normal_Spec_Doublesided":
					DiffuseTextureSampler_tex = mat.node_tree.nodes['DiffuseTextureSampler']
					NormalSpecTextureSampler_tex = mat.node_tree.nodes['NormalSpecTextureSampler']

					normal_map_node1 = mat.node_tree.nodes.new(type='ShaderNodeNormalMap')

					normal_map_node1.uv_map = "UVMap"
					normal_map_node1.inputs['Strength'].default_value = 0.4

					mat.node_tree.links.new(NormalSpecTextureSampler_tex.outputs['Color'], normal_map_node1.inputs['Color'])
					mat.node_tree.links.new(normal_map_node1.outputs['Normal'], mat.node_tree.nodes[mMaterialId].inputs['Normal'])

					mat.node_tree.links.new(DiffuseTextureSampler_tex.outputs['Alpha'], mat.node_tree.nodes[mMaterialId].inputs['Alpha'])

					mat.blend_method = 'HASHED'
					mat.shadow_method = 'HASHED'

					mat.use_backface_culling = False

					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.2
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 0.8

				elif shader_type == "Foliage_1Bit_Doublesided":
					DiffuseTextureSampler_tex = mat.node_tree.nodes['DiffuseTextureSampler']

					mat.node_tree.links.new(DiffuseTextureSampler_tex.outputs['Alpha'], mat.node_tree.nodes[mMaterialId].inputs['Alpha'])

					mat.blend_method = 'HASHED'
					mat.shadow_method = 'HASHED'

					mat.use_backface_culling = False

					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.2
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 0.8

				elif shader_type == "Foliage_Proto":
					DiffuseSampler_tex = mat.node_tree.nodes['DiffuseSampler']

					mat.node_tree.links.new(DiffuseSampler_tex.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Base Color'])
					mat.node_tree.links.new(DiffuseSampler_tex.outputs['Alpha'], mat.node_tree.nodes[mMaterialId].inputs['Alpha'])

					mat.blend_method = 'HASHED'
					mat.shadow_method = 'HASHED'

					mat.use_backface_culling = False

					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.2
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 0.8

				elif shader_type == "Foliage_Proto_Spec_Normal":
					DiffuseSampler_tex = mat.node_tree.nodes['DiffuseSampler']

					mat.node_tree.links.new(DiffuseSampler_tex.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Base Color'])
					mat.node_tree.links.new(DiffuseSampler_tex.outputs['Alpha'], mat.node_tree.nodes[mMaterialId].inputs['Alpha'])

					mat.blend_method = 'HASHED'
					mat.shadow_method = 'HASHED'

					mat.use_backface_culling = False

					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.2
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 0.8

				elif shader_type == "Foliage_LargeSprites_Proto":
					DiffuseSampler_tex = mat.node_tree.nodes['DiffuseSampler']

					mat.node_tree.links.new(DiffuseSampler_tex.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Base Color'])
					mat.node_tree.links.new(DiffuseSampler_tex.outputs['Alpha'], mat.node_tree.nodes[mMaterialId].inputs['Alpha'])

					mat.blend_method = 'HASHED'
					mat.shadow_method = 'HASHED'

					mat.use_backface_culling = False

					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.2
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 0.8

				elif shader_type == "Foliage_LargeSprites_Proto_Spec_Normal":
					DiffuseSampler_tex = mat.node_tree.nodes['DiffuseSampler']
					NormalSpecTextureSampler_tex = mat.node_tree.nodes['NormalSpecTextureSampler']

					normal_map_node1 = mat.node_tree.nodes.new(type='ShaderNodeNormalMap')

					normal_map_node1.uv_map = "UVMap"
					normal_map_node1.inputs['Strength'].default_value = 0.4

					mat.node_tree.links.new(NormalSpecTextureSampler_tex.outputs['Color'], normal_map_node1.inputs['Color'])
					mat.node_tree.links.new(normal_map_node1.outputs['Normal'], mat.node_tree.nodes[mMaterialId].inputs['Normal'])

					mat.node_tree.links.new(DiffuseSampler_tex.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Base Color'])
					mat.node_tree.links.new(DiffuseSampler_tex.outputs['Alpha'], mat.node_tree.nodes[mMaterialId].inputs['Alpha'])

					mat.blend_method = 'HASHED'
					mat.shadow_method = 'HASHED'

					mat.use_backface_culling = False

					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.2
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 0.8

				elif shader_type == "HelicopterRotor_GreyScale_Doublesided":
					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.6
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 0.2

					mat.use_backface_culling = False

				elif shader_type == "Illuminance_Diffuse_Opaque_Singlesided":
					mat_tex = mat.node_tree.nodes['IllumTextureSampler']
					mat.node_tree.links.new(mat_tex.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Emission'])

				elif shader_type == "Road_Proto":
					detailDiffuseMapSampler_tex = mat.node_tree.nodes['detailDiffuseMapSampler']
					dirtMapSampler_tex = mat.node_tree.nodes['dirtMapSampler']
					detailNormalMapSampler_tex = mat.node_tree.nodes['detailNormalMapSampler']
					crackNormalMapSampler_tex = mat.node_tree.nodes['crackNormalMapSampler']

					mix_rgb_node1 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					mix_rgb_node2 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					uv_map_node1 = mat.node_tree.nodes.new(type='ShaderNodeUVMap')
					mapping_node1 = mat.node_tree.nodes.new(type='ShaderNodeMapping')

					detailMultiplierU = parameters_Data[parameters_Names.index("detailMultiplierU")]
					detailMultiplierV = parameters_Data[parameters_Names.index("detailMultiplierV")]

					uv_map_node1.uv_map = "UVMap"
					mix_rgb_node1.blend_type = "OVERLAY"
					mix_rgb_node2.blend_type = "OVERLAY"

					mapping_node1.inputs[3].default_value[0] = detailMultiplierU[0]*1.0
					mapping_node1.inputs[3].default_value[1] = detailMultiplierV[0]*1.0

					mat.node_tree.links.new(uv_map_node1.outputs['UV'], mapping_node1.inputs[0])
					mat.node_tree.links.new(mapping_node1.outputs['Vector'], detailDiffuseMapSampler_tex.inputs['Vector'])
					mat.node_tree.links.new(mapping_node1.outputs['Vector'], detailNormalMapSampler_tex.inputs['Vector'])

					mat.node_tree.links.new(detailDiffuseMapSampler_tex.outputs['Color'], mix_rgb_node1.inputs['Color1'])
					mat.node_tree.links.new(detailDiffuseMapSampler_tex.outputs['Alpha'], mix_rgb_node1.inputs['Fac'])
					mat.node_tree.links.new(dirtMapSampler_tex.outputs['Color'], mix_rgb_node1.inputs['Color2'])
					mat.node_tree.links.new(mix_rgb_node1.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Base Color'])

					mat.node_tree.links.new(detailNormalMapSampler_tex.outputs['Color'], mix_rgb_node2.inputs['Color1'])
					mat.node_tree.links.new(crackNormalMapSampler_tex.outputs['Color'], mix_rgb_node2.inputs['Color2'])

					mat.node_tree.links.new(detailNormalMapSampler_tex.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Normal'])

					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.1
					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.2
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 1.0

				elif shader_type == "Sign_RetroReflective":
					DiffuseTextureSampler_tex = mat.node_tree.nodes['DiffuseTextureSampler']

					RetroreflectiveThreshold = parameters_Data[parameters_Names.index("RetroreflectiveThreshold")]

					mat.node_tree.links.new(DiffuseTextureSampler_tex.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Emission'])
					mat.node_tree.nodes[mMaterialId].inputs['Emission Strength'].default_value = RetroreflectiveThreshold[0]*10.0

					mat.use_backface_culling = True

				elif shader_type == "Skin_World_Diffuse_Specular_Overlay_Singlesided":
					DiffuseTextureSampler_tex = mat.node_tree.nodes['DiffuseTextureSampler']

					mat.node_tree.links.new(DiffuseTextureSampler_tex.outputs['Alpha'], mat.node_tree.nodes[mMaterialId].inputs['Alpha'])

					mat.blend_method = 'HASHED'
					mat.shadow_method = 'HASHED'

					mat.use_backface_culling = True

				elif shader_type == "Tree_Translucent_1Bit_Doublesided":
					DiffuseTextureSampler_tex = mat.node_tree.nodes['DiffuseTextureSampler']

					mat.node_tree.links.new(DiffuseTextureSampler_tex.outputs['Alpha'], mat.node_tree.nodes[mMaterialId].inputs['Alpha'])

					mat.blend_method = 'BLEND'
					mat.shadow_method = 'HASHED'

					mat.use_backface_culling = False

				elif shader_type == "Waterfall_Proto":
					DiffuseTextureSampler_tex = mat.node_tree.nodes['DiffuseTextureSampler']

					mat.node_tree.links.new(DiffuseTextureSampler_tex.outputs['Alpha'], mat.node_tree.nodes[mMaterialId].inputs['Alpha'])

					mat.blend_method = 'BLEND'
					mat.shadow_method = 'HASHED'

					mat.show_transparent_back = True

					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.0
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 0.0

				elif shader_type == "Water_Proto":
					DiffuseAndCausticsTextureSampler_tex = mat.node_tree.nodes['DiffuseAndCausticsTextureSampler']
					NormalTextureSampler_tex = mat.node_tree.nodes['NormalTextureSampler']
					RiverFloorTextureSampler_tex = mat.node_tree.nodes['RiverFloorTextureSampler']
					SurfMaskTextureSampler_tex = mat.node_tree.nodes['SurfMaskTextureSampler']
					SurfTextureSampler_tex = mat.node_tree.nodes['SurfTextureSampler']
					SurfNormalTextureSampler_tex = mat.node_tree.nodes['SurfNormalTextureSampler']

					causticTile = parameters_Data[parameters_Names.index("causticTile")]
					surfTile = parameters_Data[parameters_Names.index("surfTile")]
					normalMapTile1 = parameters_Data[parameters_Names.index("normalMapTile1")]

					uv_map_node1 = mat.node_tree.nodes.new(type='ShaderNodeUVMap')
					uv_map_node2 = mat.node_tree.nodes.new(type='ShaderNodeUVMap')
					uv_map_node3 = mat.node_tree.nodes.new(type='ShaderNodeUVMap')
					uv_map_node4 = mat.node_tree.nodes.new(type='ShaderNodeUVMap')
					mapping_node1 = mat.node_tree.nodes.new(type='ShaderNodeMapping')
					mapping_node2 = mat.node_tree.nodes.new(type='ShaderNodeMapping')
					mapping_node3 = mat.node_tree.nodes.new(type='ShaderNodeMapping')
					mapping_node4 = mat.node_tree.nodes.new(type='ShaderNodeMapping')
					normal_map_node1 = mat.node_tree.nodes.new(type='ShaderNodeNormalMap')
					mix_rgb_node1 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					mix_rgb_node2 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					mix_rgb_node3 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')

					uv_map_node1.uv_map = "UVMap"
					uv_map_node2.uv_map = "UV2Map"
					uv_map_node3.uv_map = "UVMap"
					uv_map_node4.uv_map = "UV3Map"
					normal_map_node1.uv_map = "UVMap"
					normal_map_node1.inputs['Strength'].default_value = 1.0
					mix_rgb_node1.blend_type = "OVERLAY"
					mix_rgb_node2.blend_type = "OVERLAY"
					mix_rgb_node3.blend_type = "OVERLAY"
					mix_rgb_node1.inputs['Color1'].default_value = (0.2, 0.4, 0.8, 1.0)

					mapping_node1.inputs[3].default_value[0] = causticTile[0]*1.0
					mapping_node1.inputs[3].default_value[1] = causticTile[1]*1.0

					mapping_node2.inputs[3].default_value[0] = surfTile[0]*1.0
					mapping_node2.inputs[3].default_value[1] = surfTile[1]*1.0

					mapping_node3.inputs[3].default_value[0] = normalMapTile1[0]*1.0
					mapping_node3.inputs[3].default_value[1] = normalMapTile1[1]*1.0

					mat.node_tree.links.new(uv_map_node1.outputs['UV'], mapping_node1.inputs[0])
					mat.node_tree.links.new(mapping_node1.outputs['Vector'], DiffuseAndCausticsTextureSampler_tex.inputs['Vector'])

					mat.node_tree.links.new(uv_map_node2.outputs['UV'], mapping_node2.inputs[0])
					mat.node_tree.links.new(mapping_node2.outputs['Vector'], SurfTextureSampler_tex.inputs['Vector'])
					mat.node_tree.links.new(mapping_node2.outputs['Vector'], SurfNormalTextureSampler_tex.inputs['Vector'])

					mat.node_tree.links.new(uv_map_node3.outputs['UV'], mapping_node3.inputs[0])
					mat.node_tree.links.new(mapping_node3.outputs['Vector'], NormalTextureSampler_tex.inputs['Vector'])

					mat.node_tree.links.new(uv_map_node4.outputs['UV'], mapping_node4.inputs[0])
					mat.node_tree.links.new(mapping_node4.outputs['Vector'], RiverFloorTextureSampler_tex.inputs['Vector'])

					mat.node_tree.links.new(DiffuseAndCausticsTextureSampler_tex.outputs['Alpha'], mix_rgb_node1.inputs['Fac'])
					mat.node_tree.links.new(DiffuseAndCausticsTextureSampler_tex.outputs['Color'], mix_rgb_node1.inputs['Color2'])

					mat.node_tree.links.new(SurfMaskTextureSampler_tex.outputs['Color'], mix_rgb_node2.inputs['Fac'])
					mat.node_tree.links.new(mix_rgb_node1.outputs['Color'], mix_rgb_node2.inputs['Color1'])
					mat.node_tree.links.new(SurfTextureSampler_tex.outputs['Color'], mix_rgb_node2.inputs['Color2'])

					mat.node_tree.links.new(mix_rgb_node2.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Base Color'])

					mat.node_tree.links.new(SurfMaskTextureSampler_tex.outputs['Color'], mix_rgb_node3.inputs['Fac'])
					mat.node_tree.links.new(NormalTextureSampler_tex.outputs['Color'], mix_rgb_node3.inputs['Color1'])
					mat.node_tree.links.new(SurfNormalTextureSampler_tex.outputs['Color'], mix_rgb_node3.inputs['Color2'])
					mat.node_tree.links.new(mix_rgb_node3.outputs['Color'], normal_map_node1.inputs['Color'])
					mat.node_tree.links.new(normal_map_node1.outputs['Normal'], mat.node_tree.nodes[mMaterialId].inputs['Normal'])

					mat.node_tree.nodes[mMaterialId].inputs['Base Color'].default_value = (0.5, 0.6, 0.8, 1.0)
					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.05
					mat.node_tree.nodes[mMaterialId].inputs['Specular'].default_value = 0.2
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 0.2

				elif shader_type == "Water_Proto_Cheap":
					NormalTextureSampler_tex = mat.node_tree.nodes['NormalTextureSampler']

					normalMapTile1 = parameters_Data[parameters_Names.index("normalMapTile1")]

					uv_map_node1 = mat.node_tree.nodes.new(type='ShaderNodeUVMap')
					mapping_node1 = mat.node_tree.nodes.new(type='ShaderNodeMapping')
					normal_map_node1 = mat.node_tree.nodes.new(type='ShaderNodeNormalMap')

					uv_map_node1.uv_map = "UVMap"
					normal_map_node1.uv_map = "UVMap"
					normal_map_node1.inputs['Strength'].default_value = 1.0

					mapping_node1.inputs[3].default_value[0] = normalMapTile1[0]*1.0
					mapping_node1.inputs[3].default_value[1] = normalMapTile1[1]*1.0

					mat.node_tree.links.new(uv_map_node1.outputs['UV'], mapping_node1.inputs[0])
					mat.node_tree.links.new(mapping_node1.outputs['Vector'], NormalTextureSampler_tex.inputs['Vector'])
					mat.node_tree.links.new(NormalTextureSampler_tex.outputs['Color'], normal_map_node1.inputs['Color'])
					mat.node_tree.links.new(normal_map_node1.outputs['Normal'], mat.node_tree.nodes[mMaterialId].inputs['Normal'])

					mat.node_tree.nodes[mMaterialId].inputs['Base Color'].default_value = (0.22, 0.43, 0.74, 1.0)
					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.05
					mat.node_tree.nodes[mMaterialId].inputs['Specular'].default_value = 0.2
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 0.2

				elif shader_type == "World_CopStudio_Specular_Reflective_Singlesided":
					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 1.0
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 0.15

					mat.use_backface_culling = True

				elif shader_type == "World_Diffuse_1Bit_Dirt_Normal_Specular_Overlay_Singlesided":
					DiffuseTextureSampler_tex = mat.node_tree.nodes['DiffuseTextureSampler']
					OverlayTextureSampler_tex = mat.node_tree.nodes['OverlayTextureSampler']
					NormalTextureSampler_tex = mat.node_tree.nodes['NormalTextureSampler']

					DirtTint = parameters_Data[parameters_Names.index("DirtTint")]

					mix_rgb_node1 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					uv_map_node1 = mat.node_tree.nodes.new(type='ShaderNodeUVMap')

					uv_map_node1.uv_map = "UV2Map"
					mix_rgb_node1.blend_type = "OVERLAY"
					mix_rgb_node1.inputs['Color2'].default_value = DirtTint

					mat.node_tree.links.new(uv_map_node1.outputs['UV'], OverlayTextureSampler_tex.inputs['Vector'])

					mat.node_tree.links.new(OverlayTextureSampler_tex.outputs['Color'], mix_rgb_node1.inputs['Fac'])
					mat.node_tree.links.new(DiffuseTextureSampler_tex.outputs['Color'], mix_rgb_node1.inputs['Color1'])
					mat.node_tree.links.new(mix_rgb_node1.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Base Color'])

					mat.node_tree.links.new(DiffuseTextureSampler_tex.outputs['Alpha'], mat.node_tree.nodes[mMaterialId].inputs['Alpha'])

					mat.node_tree.links.new(NormalTextureSampler_tex.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Normal'])

					mat.blend_method = 'HASHED'
					mat.shadow_method = 'HASHED'

					mat.use_backface_culling = True

				elif shader_type == "World_Diffuse_Dirt_Normal_SpecMap_Overlay_Singlesided":
					DiffuseTextureSampler_tex = mat.node_tree.nodes['DiffuseTextureSampler']
					OverlayTextureSampler_tex = mat.node_tree.nodes['OverlayTextureSampler']
					NormalTextureSampler_tex = mat.node_tree.nodes['NormalTextureSampler']

					DirtTint = parameters_Data[parameters_Names.index("DirtTint")]

					# mix_rgb_node1 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					# uv_map_node1 = mat.node_tree.nodes.new(type='ShaderNodeUVMap')

					# uv_map_node1.uv_map = "UV2Map"
					# mix_rgb_node1.blend_type = "OVERLAY"
					# mix_rgb_node1.inputs['Color2'].default_value = DirtTint

					#mat.node_tree.links.new(uv_map_node1.outputs['UV'], OverlayTextureSampler_tex.inputs['Vector'])

					#mat.node_tree.links.new(OverlayTextureSampler_tex.outputs['Color'], mix_rgb_node1.inputs['Fac'])
					#mat.node_tree.links.new(DiffuseTextureSampler_tex.outputs['Color'], mix_rgb_node1.inputs['Color1'])
					#mat.node_tree.links.new(mix_rgb_node1.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Base Color'])

					mat.node_tree.links.new(NormalTextureSampler_tex.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Normal'])

					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.0
					mat.node_tree.nodes[mMaterialId].inputs['Specular'].default_value = 0.25
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 0.75

					mat.use_backface_culling = True

				elif shader_type == "World_Diffuse_Dirt_Normal_Specular_Overlay_Singlesided":
					DiffuseTextureSampler_tex = mat.node_tree.nodes['DiffuseTextureSampler']
					OverlayTextureSampler_tex = mat.node_tree.nodes['OverlayTextureSampler']
					NormalTextureSampler_tex = mat.node_tree.nodes['NormalTextureSampler']

					DirtTint = parameters_Data[parameters_Names.index("DirtTint")]

					mix_rgb_node1 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					uv_map_node1 = mat.node_tree.nodes.new(type='ShaderNodeUVMap')

					uv_map_node1.uv_map = "UV2Map"
					mix_rgb_node1.blend_type = "OVERLAY"
					mix_rgb_node1.inputs['Color2'].default_value = DirtTint

					mat.node_tree.links.new(uv_map_node1.outputs['UV'], OverlayTextureSampler_tex.inputs['Vector'])

					mat.node_tree.links.new(OverlayTextureSampler_tex.outputs['Color'], mix_rgb_node1.inputs['Fac'])
					mat.node_tree.links.new(DiffuseTextureSampler_tex.outputs['Color'], mix_rgb_node1.inputs['Color1'])
					mat.node_tree.links.new(mix_rgb_node1.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Base Color'])

					mat.node_tree.links.new(NormalTextureSampler_tex.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Normal'])

					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.0
					mat.node_tree.nodes[mMaterialId].inputs['Specular'].default_value = 0.25
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 0.75

					mat.use_backface_culling = True

				elif shader_type == "World_Diffuse_Normal_SpecMap_Overlay_Singlesided":
					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.5
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 0.4

					mat.use_backface_culling = True

				elif shader_type == "World_Diffuse_Normal_SpecMap":
					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.0
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 1.0

				elif shader_type == "World_Diffuse_Reflective_Overlay_Lightmap_Singlesided":
					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.3
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 1.0

					mat.use_backface_culling = True

				elif shader_type == "World_Diffuse_Specular_Singlesided":
					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.1
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 0.4

					mat.use_backface_culling = True

				elif shader_type == "World_Diffuse_Specular_1Bit_Lightmap_Doublesided":
					DiffuseTextureSampler_tex = mat.node_tree.nodes['DiffuseTextureSampler']

					mat.node_tree.links.new(DiffuseTextureSampler_tex.outputs['Alpha'], mat.node_tree.nodes[mMaterialId].inputs['Alpha'])

					mat.blend_method = 'HASHED'
					mat.shadow_method = 'HASHED'

					mat.use_backface_culling = False

					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.2
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 0.8

				elif shader_type == "World_Diffuse_Specular_1Bit_LightmapNight_Doublesided":
					DiffuseTextureSampler_tex = mat.node_tree.nodes['DiffuseTextureSampler']

					mat.node_tree.links.new(DiffuseTextureSampler_tex.outputs['Alpha'], mat.node_tree.nodes[mMaterialId].inputs['Alpha'])

					mat.blend_method = 'HASHED'
					mat.shadow_method = 'HASHED'

					mat.use_backface_culling = False

					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.2
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 0.8

				elif shader_type == "World_Diffuse_Specular_FlashingNeon_Singlesided":
					DiffuseTextureSampler_tex = mat.node_tree.nodes['DiffuseTextureSampler']

					mat.node_tree.links.new(DiffuseTextureSampler_tex.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Emission'])

					mat.node_tree.nodes[mMaterialId].inputs['Emission Strength'].default_value = 5.0

					mat.use_backface_culling = True

				elif shader_type == "World_Diffuse_Specular_Normal_Parallax_Singlesided":
					DiffuseTextureSampler_tex = mat.node_tree.nodes['DiffuseTextureSampler']

					window_Tint = parameters_Data[parameters_Names.index("window_Tint")]

					mix_rgb_node1 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')

					mix_rgb_node1.inputs['Color1'].default_value = window_Tint

					mat.node_tree.links.new(DiffuseTextureSampler_tex.outputs['Alpha'], mix_rgb_node1.inputs['Fac'])
					mat.node_tree.links.new(DiffuseTextureSampler_tex.outputs['Color'], mix_rgb_node1.inputs['Color2'])
					mat.node_tree.links.new(mix_rgb_node1.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Base Color'])

					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.6
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 0.2

					mat.use_backface_culling = True

				elif shader_type == "World_Diffuse_Specular_Normal_Overlay_Lightmap_Singlesided":
					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.0
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 1.0

					mat.use_backface_culling = True

				elif shader_type == "World_Diffuse_Specular_Overlay_Lightmap_Singlesided":
					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.0
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 1.0

					mat.use_backface_culling = True

				elif shader_type == "World_Diffuse_Specular_Overlay_LightmapNight_Singlesided":
					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.0
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 1.0

					mat.use_backface_culling = True

				elif shader_type == "World_Diffuse_Specular_Parallax_Singlesided":
					DiffuseTextureSampler_tex = mat.node_tree.nodes['DiffuseTextureSampler']

					window_Tint = parameters_Data[parameters_Names.index("window_Tint")]

					mix_rgb_node1 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')

					mix_rgb_node1.inputs['Color2'].default_value = window_Tint

					mat.node_tree.links.new(DiffuseTextureSampler_tex.outputs['Alpha'], mix_rgb_node1.inputs['Fac'])
					mat.node_tree.links.new(DiffuseTextureSampler_tex.outputs['Color'], mix_rgb_node1.inputs['Color1'])
					mat.node_tree.links.new(mix_rgb_node1.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Base Color'])

					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.6
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 0.2

					mat.use_backface_culling = True

				elif shader_type == "World_Diffuse_Specular_Normal_Parallax_WindowTex_Singlesided":
					DiffuseTextureSampler_tex = mat.node_tree.nodes['DiffuseTextureSampler']
					WindowTintSampler_tex = mat.node_tree.nodes['WindowTintSampler']

					mix_rgb_node1 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					uv_map_node1 = mat.node_tree.nodes.new(type='ShaderNodeUVMap')

					uv_map_node1.uv_map = "UV3Map"

					mat.node_tree.links.new(uv_map_node1.outputs['UV'], WindowTintSampler_tex.inputs['Vector'])

					mat.node_tree.links.new(DiffuseTextureSampler_tex.outputs['Alpha'], mix_rgb_node1.inputs['Fac'])
					mat.node_tree.links.new(DiffuseTextureSampler_tex.outputs['Color'], mix_rgb_node1.inputs['Color2'])
					mat.node_tree.links.new(WindowTintSampler_tex.outputs['Color'], mix_rgb_node1.inputs['Color1'])
					mat.node_tree.links.new(mix_rgb_node1.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Base Color'])

					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.6
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 0.2

					mat.use_backface_culling = True

				elif shader_type == "World_Diffuse_Specular_Overlay_Singlesided":
					DiffuseTextureSampler_tex = mat.node_tree.nodes['DiffuseTextureSampler']

					mat.node_tree.links.new(DiffuseTextureSampler_tex.outputs['Alpha'], mat.node_tree.nodes[mMaterialId].inputs['Alpha'])

					mat.blend_method = 'HASHED'
					mat.shadow_method = 'HASHED'

					mat.use_backface_culling = True

					mat.node_tree.nodes[mMaterialId].inputs['Specular'].default_value = 0.2

				elif shader_type == "World_Diffuse_Specular_Reflective_Singlesided":
					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.6
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 0.5

					mat.use_backface_culling = True

				elif shader_type == "World_Diffuse_Specular_Overlay_Illuminance_Singlesided":
					DiffuseTextureSampler_tex = mat.node_tree.nodes['DiffuseTextureSampler']
					OverlayTextureSampler_tex = mat.node_tree.nodes['OverlayTextureSampler']
					IlluminanceTextureSampler_tex = mat.node_tree.nodes['IlluminanceTextureSampler']

					materialDiffuse = parameters_Data[parameters_Names.index("materialDiffuse")]

					mix_rgb_node1 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')

					mix_rgb_node1.blend_type = "OVERLAY"
					mix_rgb_node1.inputs['Color1'].default_value = materialDiffuse

					mat.node_tree.links.new(OverlayTextureSampler_tex.outputs['Color'], mix_rgb_node1.inputs['Fac'])
					mat.node_tree.links.new(DiffuseTextureSampler_tex.outputs['Color'], mix_rgb_node1.inputs['Color1'])
					mat.node_tree.links.new(mix_rgb_node1.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Base Color'])
					mat.node_tree.links.new(IlluminanceTextureSampler_tex.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Emission'])

					mat.node_tree.nodes[mMaterialId].inputs['Emission Strength'].default_value = 1.0

					mat.blend_method = 'HASHED'
					mat.shadow_method = 'HASHED'

					mat.use_backface_culling = True

				elif shader_type == "World_Diffuse_Specular_Overlay_IlluminanceNight_Singlesided":
					DiffuseTextureSampler_tex = mat.node_tree.nodes['DiffuseTextureSampler']
					IlluminanceTextureSampler_tex = mat.node_tree.nodes['IlluminanceTextureSampler']

					mat.node_tree.links.new(DiffuseTextureSampler_tex.outputs['Alpha'], mat.node_tree.nodes[mMaterialId].inputs['Alpha'])
					mat.node_tree.links.new(IlluminanceTextureSampler_tex.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Emission'])

					mat.node_tree.nodes[mMaterialId].inputs['Emission Strength'].default_value = 0.6

					mat.blend_method = 'HASHED'
					mat.shadow_method = 'HASHED'

					mat.use_backface_culling = True

				elif shader_type == "World_DiffuseBlend_Normal_Overlay_Singlesided":
					DiffuseTextureSampler_tex = mat.node_tree.nodes['DiffuseTextureSampler']
					Diffuse2TextureSampler_tex = mat.node_tree.nodes['Diffuse2TextureSampler']
					OverlayTextureSampler_tex = mat.node_tree.nodes['OverlayTextureSampler']

					mix_rgb_node1 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					uv_map_node1 = mat.node_tree.nodes.new(type='ShaderNodeUVMap')

					mix_rgb_node1.blend_type = "OVERLAY"

					uv_map_node1.uv_map = "UV2Map"
					mat.node_tree.links.new(uv_map_node1.outputs['UV'], OverlayTextureSampler_tex.inputs['Vector'])

					mat.node_tree.links.new(OverlayTextureSampler_tex.outputs['Color'], mix_rgb_node1.inputs['Fac'])
					mat.node_tree.links.new(DiffuseTextureSampler_tex.outputs['Color'], mix_rgb_node1.inputs['Color1'])
					mat.node_tree.links.new(Diffuse2TextureSampler_tex.outputs['Color'], mix_rgb_node1.inputs['Color2'])
					mat.node_tree.links.new(mix_rgb_node1.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Base Color'])

					mat.use_backface_culling = True

				elif shader_type == "World_DiffuseBlend_Normal_Overlay_Lightmap_Singlesided":
					DiffuseTextureSampler_tex = mat.node_tree.nodes['DiffuseTextureSampler']
					Diffuse2TextureSampler_tex = mat.node_tree.nodes['Diffuse2TextureSampler']

					mix_rgb_node1 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					uv_map_node1 = mat.node_tree.nodes.new(type='ShaderNodeUVMap')

					mix_rgb_node1.blend_type = "MIX"

					uv_map_node1.uv_map = "UVMap"
					mat.node_tree.links.new(uv_map_node1.outputs['UV'], Diffuse2TextureSampler_tex.inputs['Vector'])

					mat.node_tree.links.new(DiffuseTextureSampler_tex.outputs['Color'], mix_rgb_node1.inputs['Color1'])
					mat.node_tree.links.new(Diffuse2TextureSampler_tex.outputs['Color'], mix_rgb_node1.inputs['Color2'])
					mat.node_tree.links.new(mix_rgb_node1.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Base Color'])

					mat.use_backface_culling = True

					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.2
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 0.4

				elif shader_type == "World_DiffuseBlend_Normal_Overlay_LightmapNight_Singlesided":
					DiffuseTextureSampler_tex = mat.node_tree.nodes['DiffuseTextureSampler']
					Diffuse2TextureSampler_tex = mat.node_tree.nodes['Diffuse2TextureSampler']

					mix_rgb_node1 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					uv_map_node1 = mat.node_tree.nodes.new(type='ShaderNodeUVMap')

					mix_rgb_node1.blend_type = "MIX"

					uv_map_node1.uv_map = "UVMap"
					mat.node_tree.links.new(uv_map_node1.outputs['UV'], Diffuse2TextureSampler_tex.inputs['Vector'])

					mat.node_tree.links.new(DiffuseTextureSampler_tex.outputs['Color'], mix_rgb_node1.inputs['Color1'])
					mat.node_tree.links.new(Diffuse2TextureSampler_tex.outputs['Color'], mix_rgb_node1.inputs['Color2'])
					mat.node_tree.links.new(mix_rgb_node1.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Base Color'])

					mat.use_backface_culling = True

					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.2
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 0.4

				elif shader_type == "World_DiffuseBlend_Specular_Overlay_Singlesided":
					DiffuseTextureSampler_tex = mat.node_tree.nodes['DiffuseTextureSampler']
					Diffuse2TextureSampler_tex = mat.node_tree.nodes['Diffuse2TextureSampler']
					OverlayTextureSampler_tex = mat.node_tree.nodes['OverlayTextureSampler']

					mix_rgb_node1 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					uv_map_node1 = mat.node_tree.nodes.new(type='ShaderNodeUVMap')

					mix_rgb_node1.blend_type = "OVERLAY"

					uv_map_node1.uv_map = "UV2Map"
					mat.node_tree.links.new(uv_map_node1.outputs['UV'], OverlayTextureSampler_tex.inputs['Vector'])

					mat.node_tree.links.new(OverlayTextureSampler_tex.outputs['Color'], mix_rgb_node1.inputs['Fac'])
					mat.node_tree.links.new(DiffuseTextureSampler_tex.outputs['Color'], mix_rgb_node1.inputs['Color1'])
					mat.node_tree.links.new(Diffuse2TextureSampler_tex.outputs['Color'], mix_rgb_node1.inputs['Color2'])
					mat.node_tree.links.new(mix_rgb_node1.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Base Color'])

					mat.use_backface_culling = True

				elif shader_type == "World_Diffuse_Normal_SpecMap_Singlesided":
					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.3
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 0.7

					mat.use_backface_culling = True

				elif shader_type == "World_Diffuse_Specular_Illuminance_Singlesided":
					IlluminanceTextureSampler_tex = mat.node_tree.nodes['IlluminanceTextureSampler']

					SpecularPower = parameters_Data[parameters_Names.index("SpecularPower")]

					mat.node_tree.links.new(IlluminanceTextureSampler_tex.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Emission'])
					mat.node_tree.nodes[mMaterialId].inputs['Emission Strength'].default_value = SpecularPower[0]

				elif shader_type == "World_Normal_Reflective_Overlay_Lightmap_Singlesided":
					DiffuseTextureSampler_tex = mat.node_tree.nodes['DiffuseTextureSampler']
					OverlayTextureSampler_tex = mat.node_tree.nodes['OverlayTextureSampler']

					uv_map_node1 = mat.node_tree.nodes.new(type='ShaderNodeUVMap')
					uv_map_node1.uv_map = "UV2Map"
					mat.node_tree.links.new(uv_map_node1.outputs['UV'], OverlayTextureSampler_tex.inputs['Vector'])

					materialDiffuse = parameters_Data[parameters_Names.index("materialDiffuse")]

					mix_rgb_node1 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')

					mix_rgb_node1.blend_type = "OVERLAY"
					mix_rgb_node1.inputs['Color1'].default_value = materialDiffuse

					mat.node_tree.links.new(DiffuseTextureSampler_tex.outputs['Color'], mix_rgb_node1.inputs['Fac'])
					mat.node_tree.links.new(OverlayTextureSampler_tex.outputs['Color'], mix_rgb_node1.inputs['Color1'])
					mat.node_tree.links.new(mix_rgb_node1.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Base Color'])

					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.6
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 0.2

					mat.use_backface_culling = True

				elif shader_type == "World_Normal_Specular_Overlay_Singlesided":
					NormalTextureSampler_tex = mat.node_tree.nodes['NormalTextureSampler']

					mat.node_tree.links.new(NormalTextureSampler_tex.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Normal'])

					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.5
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 0.4

					mat.use_backface_culling = True

				elif shader_type == "World_Normal_Specular_Overlay_Lightmap_Singlesided":
					NormalTextureSampler_tex = mat.node_tree.nodes['NormalTextureSampler']

					mat.node_tree.links.new(NormalTextureSampler_tex.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Normal'])

					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.6
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 1.0

					mat.use_backface_culling = True

				elif shader_type == "World_Normal_Specular_Overlay_LightmapNight_Singlesided":
					NormalTextureSampler_tex = mat.node_tree.nodes['NormalTextureSampler']

					mat.node_tree.links.new(NormalTextureSampler_tex.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Normal'])

					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.6
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 1.0

					mat.use_backface_culling = True

				elif shader_type == "World_Tourbus_Normal_Reflective_Overlay_Singlesided":
					DiffuseTextureSampler_tex = mat.node_tree.nodes['DiffuseTextureSampler']
					OverlayTextureSampler_tex = mat.node_tree.nodes['OverlayTextureSampler']

					materialDiffuse = parameters_Data[parameters_Names.index("materialDiffuse")]

					mix_rgb_node1 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')

					mix_rgb_node1.blend_type = "OVERLAY"
					mix_rgb_node1.inputs['Color1'].default_value = materialDiffuse

					mat.node_tree.links.new(OverlayTextureSampler_tex.outputs['Color'], mix_rgb_node1.inputs['Fac'])
					mat.node_tree.links.new(DiffuseTextureSampler_tex.outputs['Color'], mix_rgb_node1.inputs['Color2'])
					mat.node_tree.links.new(mix_rgb_node1.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Base Color'])

					mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.7
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 0.25

					mat.use_backface_culling = True

				elif shader_type == "HidingSpot_Proto":
					Tiling1TextureSampler_tex = mat.node_tree.nodes['Tiling1TextureSampler']
					Tiling2TextureSampler_tex = mat.node_tree.nodes['Tiling2TextureSampler']
					Tiling3TextureSampler_tex = mat.node_tree.nodes['Tiling3TextureSampler']
					MaskTextureSampler_tex = mat.node_tree.nodes['MaskTextureSampler']
					DecalTextureSampler_tex = mat.node_tree.nodes['DecalTextureSampler']

					mix_rgb_node1 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					mix_rgb_node2 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					mix_rgb_node3 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					uv_map_node = mat.node_tree.nodes.new(type='ShaderNodeUVMap')
					mapping_node1 = mat.node_tree.nodes.new(type='ShaderNodeMapping')
					mapping_node2 = mat.node_tree.nodes.new(type='ShaderNodeMapping')
					mapping_node3 = mat.node_tree.nodes.new(type='ShaderNodeMapping')
					mapping_node4 = mat.node_tree.nodes.new(type='ShaderNodeMapping')

					mix_rgb_node3.blend_type = "OVERLAY"
					mix_rgb_node3.inputs['Fac'].default_value = 0.05
					uv_map_node.uv_map = "UVMap"

					Tiling_Ratios_X = parameters_Data[parameters_Names.index("Tiling_Ratios_X")]
					Tiling_Ratios_Y = parameters_Data[parameters_Names.index("Tiling_Ratios_Y")]
					Tiling_Ratio_Noise = parameters_Data[parameters_Names.index("Tiling_Ratio_Noise")]
					#decalTilingRatios = parameters_Data[parameters_Names.index("decalTilingRatios")]

					mat.node_tree.links.new(uv_map_node.outputs['UV'], mapping_node1.inputs[0])
					mat.node_tree.links.new(uv_map_node.outputs['UV'], mapping_node2.inputs[0])
					mat.node_tree.links.new(uv_map_node.outputs['UV'], mapping_node3.inputs[0])
					mat.node_tree.links.new(uv_map_node.outputs['UV'], mapping_node4.inputs[0])

					mapping_node1.inputs[3].default_value[0] = Tiling_Ratios_X[0]*1000
					mapping_node1.inputs[3].default_value[1] = Tiling_Ratios_Y[0]*1000

					mapping_node2.inputs[3].default_value[0] = Tiling_Ratios_X[1]*1000
					mapping_node2.inputs[3].default_value[1] = Tiling_Ratios_Y[1]*1000

					mapping_node3.inputs[3].default_value[0] = Tiling_Ratios_X[2]*1000
					mapping_node3.inputs[3].default_value[1] = Tiling_Ratios_Y[2]*1000

					#mapping_node4.inputs[3].default_value[0] = decalTilingRatios[0]*10.0
					#mapping_node4.inputs[3].default_value[1] = decalTilingRatios[1]*10.0

					mat.node_tree.links.new(mapping_node1.outputs['Vector'], Tiling1TextureSampler_tex.inputs['Vector'])
					mat.node_tree.links.new(mapping_node2.outputs['Vector'], Tiling2TextureSampler_tex.inputs['Vector'])
					mat.node_tree.links.new(mapping_node3.outputs['Vector'], Tiling3TextureSampler_tex.inputs['Vector'])
					mat.node_tree.links.new(mapping_node4.outputs['Vector'], DecalTextureSampler_tex.inputs['Vector'])

					mat.node_tree.links.new(Tiling2TextureSampler_tex.outputs['Color'], mix_rgb_node1.inputs['Color1'])
					mat.node_tree.links.new(Tiling3TextureSampler_tex.outputs['Color'], mix_rgb_node1.inputs['Color2'])

					mat.node_tree.links.new(Tiling1TextureSampler_tex.outputs['Color'], mix_rgb_node2.inputs['Color2'])
					mat.node_tree.links.new(mix_rgb_node1.outputs['Color'], mix_rgb_node2.inputs['Color1'])

					mat.node_tree.links.new(mix_rgb_node2.outputs['Color'], mix_rgb_node3.inputs['Color1'])
					mat.node_tree.links.new(DecalTextureSampler_tex.outputs['Color'], mix_rgb_node3.inputs['Color2'])

					mat.node_tree.links.new(mix_rgb_node3.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Base Color'])
					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 1.0

					separate_rgb_node1 = mat.node_tree.nodes.new(type='ShaderNodeSeparateRGB')
					uv_map_node2 = mat.node_tree.nodes.new(type='ShaderNodeUVMap')
					uv_map_node2.uv_map = "UVMap"

					mat.node_tree.links.new(uv_map_node2.outputs['UV'], MaskTextureSampler_tex.inputs['Vector'])
					mat.node_tree.links.new(MaskTextureSampler_tex.outputs['Color'], separate_rgb_node1.inputs['Image'])
					mat.node_tree.links.new(separate_rgb_node1.outputs['G'], mix_rgb_node1.inputs['Fac'])
					mat.node_tree.links.new(separate_rgb_node1.outputs['R'], mix_rgb_node2.inputs['Fac'])

				elif shader_type == "HidingSpot_Proto_Lightmap":
					Tiling1TextureSampler_tex = mat.node_tree.nodes['Tiling1TextureSampler']
					Tiling2TextureSampler_tex = mat.node_tree.nodes['Tiling2TextureSampler']
					Tiling3TextureSampler_tex = mat.node_tree.nodes['Tiling3TextureSampler']
					NoiseTextureSampler_tex = mat.node_tree.nodes['NoiseTextureSampler']
					MaskTextureSampler_tex = mat.node_tree.nodes['MaskTextureSampler']
					DecalTextureSampler_tex = mat.node_tree.nodes['DecalTextureSampler']
					TyreMarkTextureSampler_tex = mat.node_tree.nodes['TyreMarkTextureSampler']
					Tiling1NormalSampler_tex = mat.node_tree.nodes['Tiling1NormalSampler']
					Tiling2NormalSampler_tex = mat.node_tree.nodes['Tiling2NormalSampler']
					Tiling3NormalSampler_tex = mat.node_tree.nodes['Tiling3NormalSampler']

					mix_rgb_node1 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					mix_rgb_node2 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					separate_rgb_node1 = mat.node_tree.nodes.new(type='ShaderNodeSeparateRGB')
					uv_map_node1 = mat.node_tree.nodes.new(type='ShaderNodeUVMap')
					uv_map_node2 = mat.node_tree.nodes.new(type='ShaderNodeUVMap')
					uv_map_node3 = mat.node_tree.nodes.new(type='ShaderNodeUVMap')
					uv_map_node4 = mat.node_tree.nodes.new(type='ShaderNodeUVMap')
					mapping_node1 = mat.node_tree.nodes.new(type='ShaderNodeMapping')
					mapping_node2 = mat.node_tree.nodes.new(type='ShaderNodeMapping')
					mapping_node3 = mat.node_tree.nodes.new(type='ShaderNodeMapping')
					mapping_node4 = mat.node_tree.nodes.new(type='ShaderNodeMapping')

					uv_map_node1.uv_map = "UV2Map"
					uv_map_node2.uv_map = "UV3Map"
					uv_map_node3.uv_map = "UV3Map"
					uv_map_node4.uv_map = "UVMap"

					Tiling_Ratios_X = parameters_Data[parameters_Names.index("Tiling_Ratios_X")]
					Tiling_Ratios_Y = parameters_Data[parameters_Names.index("Tiling_Ratios_Y")]
					Tiling_Ratio_Noise = parameters_Data[parameters_Names.index("Tiling_Ratio_Noise")]

					mat.node_tree.links.new(uv_map_node1.outputs['UV'], mapping_node1.inputs[0])
					mat.node_tree.links.new(uv_map_node1.outputs['UV'], mapping_node2.inputs[0])
					mat.node_tree.links.new(uv_map_node1.outputs['UV'], mapping_node3.inputs[0])
					mat.node_tree.links.new(uv_map_node1.outputs['UV'], mapping_node4.inputs[0])
					mat.node_tree.links.new(uv_map_node2.outputs['UV'], DecalTextureSampler_tex.inputs['Vector'])
					mat.node_tree.links.new(uv_map_node3.outputs['UV'], TyreMarkTextureSampler_tex.inputs['Vector'])
					mat.node_tree.links.new(uv_map_node4.outputs['UV'], MaskTextureSampler_tex.inputs['Vector'])

					mapping_node1.inputs[3].default_value[0] = Tiling_Ratios_X[0]*100
					mapping_node1.inputs[3].default_value[1] = Tiling_Ratios_Y[0]*100

					mapping_node2.inputs[3].default_value[0] = Tiling_Ratios_X[1]*100
					mapping_node2.inputs[3].default_value[1] = Tiling_Ratios_Y[1]*100

					mapping_node3.inputs[3].default_value[0] = Tiling_Ratios_X[2]*100
					mapping_node3.inputs[3].default_value[1] = Tiling_Ratios_Y[2]*100

					mapping_node4.inputs[3].default_value[0] = Tiling_Ratio_Noise[0]*100
					mapping_node4.inputs[3].default_value[1] = Tiling_Ratio_Noise[0]*100

					mat.node_tree.links.new(mapping_node1.outputs['Vector'], Tiling1TextureSampler_tex.inputs['Vector'])
					mat.node_tree.links.new(mapping_node2.outputs['Vector'], Tiling2TextureSampler_tex.inputs['Vector'])
					mat.node_tree.links.new(mapping_node3.outputs['Vector'], Tiling3TextureSampler_tex.inputs['Vector'])
					mat.node_tree.links.new(mapping_node4.outputs['Vector'], NoiseTextureSampler_tex.inputs['Vector'])

					mat.node_tree.links.new(MaskTextureSampler_tex.outputs['Color'], separate_rgb_node1.inputs['Image'])
					mat.node_tree.links.new(separate_rgb_node1.outputs['B'], mix_rgb_node1.inputs['Fac'])
					mat.node_tree.links.new(separate_rgb_node1.outputs['R'], mix_rgb_node2.inputs['Fac'])

					mat.node_tree.links.new(Tiling1TextureSampler_tex.outputs['Color'], mix_rgb_node1.inputs['Color1'])
					mat.node_tree.links.new(Tiling3TextureSampler_tex.outputs['Color'], mix_rgb_node1.inputs['Color2'])

					mat.node_tree.links.new(Tiling2TextureSampler_tex.outputs['Color'], mix_rgb_node2.inputs['Color1'])
					mat.node_tree.links.new(mix_rgb_node1.outputs['Color'], mix_rgb_node2.inputs['Color2'])

					mat.node_tree.links.new(mix_rgb_node2.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Base Color'])

					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 1.0

				elif shader_type == "HidingSpot_Proto_LightmapNight":
					Tiling1TextureSampler_tex = mat.node_tree.nodes['Tiling1TextureSampler']
					Tiling2TextureSampler_tex = mat.node_tree.nodes['Tiling2TextureSampler']
					Tiling3TextureSampler_tex = mat.node_tree.nodes['Tiling3TextureSampler']
					NoiseTextureSampler_tex = mat.node_tree.nodes['NoiseTextureSampler']
					MaskTextureSampler_tex = mat.node_tree.nodes['MaskTextureSampler']
					DecalTextureSampler_tex = mat.node_tree.nodes['DecalTextureSampler']
					TyreMarkTextureSampler_tex = mat.node_tree.nodes['TyreMarkTextureSampler']
					Tiling1NormalSampler_tex = mat.node_tree.nodes['Tiling1NormalSampler']
					Tiling2NormalSampler_tex = mat.node_tree.nodes['Tiling2NormalSampler']
					Tiling3NormalSampler_tex = mat.node_tree.nodes['Tiling3NormalSampler']

					mix_rgb_node1 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					mix_rgb_node2 = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					separate_rgb_node1 = mat.node_tree.nodes.new(type='ShaderNodeSeparateRGB')
					uv_map_node1 = mat.node_tree.nodes.new(type='ShaderNodeUVMap')
					uv_map_node2 = mat.node_tree.nodes.new(type='ShaderNodeUVMap')
					uv_map_node3 = mat.node_tree.nodes.new(type='ShaderNodeUVMap')
					uv_map_node4 = mat.node_tree.nodes.new(type='ShaderNodeUVMap')
					mapping_node1 = mat.node_tree.nodes.new(type='ShaderNodeMapping')
					mapping_node2 = mat.node_tree.nodes.new(type='ShaderNodeMapping')
					mapping_node3 = mat.node_tree.nodes.new(type='ShaderNodeMapping')
					mapping_node4 = mat.node_tree.nodes.new(type='ShaderNodeMapping')

					uv_map_node1.uv_map = "UV2Map"
					uv_map_node2.uv_map = "UV3Map"
					uv_map_node3.uv_map = "UV3Map"
					uv_map_node4.uv_map = "UVMap"

					Tiling_Ratios_X = parameters_Data[parameters_Names.index("Tiling_Ratios_X")]
					Tiling_Ratios_Y = parameters_Data[parameters_Names.index("Tiling_Ratios_Y")]
					Tiling_Ratio_Noise = parameters_Data[parameters_Names.index("Tiling_Ratio_Noise")]

					mat.node_tree.links.new(uv_map_node1.outputs['UV'], mapping_node1.inputs[0])
					mat.node_tree.links.new(uv_map_node1.outputs['UV'], mapping_node2.inputs[0])
					mat.node_tree.links.new(uv_map_node1.outputs['UV'], mapping_node3.inputs[0])
					mat.node_tree.links.new(uv_map_node1.outputs['UV'], mapping_node4.inputs[0])
					mat.node_tree.links.new(uv_map_node2.outputs['UV'], DecalTextureSampler_tex.inputs['Vector'])
					mat.node_tree.links.new(uv_map_node3.outputs['UV'], TyreMarkTextureSampler_tex.inputs['Vector'])
					mat.node_tree.links.new(uv_map_node4.outputs['UV'], MaskTextureSampler_tex.inputs['Vector'])

					mapping_node1.inputs[3].default_value[0] = Tiling_Ratios_X[0]*100
					mapping_node1.inputs[3].default_value[1] = Tiling_Ratios_Y[0]*100

					mapping_node2.inputs[3].default_value[0] = Tiling_Ratios_X[1]*100
					mapping_node2.inputs[3].default_value[1] = Tiling_Ratios_Y[1]*100

					mapping_node3.inputs[3].default_value[0] = Tiling_Ratios_X[2]*100
					mapping_node3.inputs[3].default_value[1] = Tiling_Ratios_Y[2]*100

					mapping_node4.inputs[3].default_value[0] = Tiling_Ratio_Noise[0]*100
					mapping_node4.inputs[3].default_value[1] = Tiling_Ratio_Noise[0]*100

					mat.node_tree.links.new(mapping_node1.outputs['Vector'], Tiling1TextureSampler_tex.inputs['Vector'])
					mat.node_tree.links.new(mapping_node2.outputs['Vector'], Tiling2TextureSampler_tex.inputs['Vector'])
					mat.node_tree.links.new(mapping_node3.outputs['Vector'], Tiling3TextureSampler_tex.inputs['Vector'])
					mat.node_tree.links.new(mapping_node4.outputs['Vector'], NoiseTextureSampler_tex.inputs['Vector'])

					mat.node_tree.links.new(MaskTextureSampler_tex.outputs['Color'], separate_rgb_node1.inputs['Image'])
					mat.node_tree.links.new(separate_rgb_node1.outputs['B'], mix_rgb_node1.inputs['Fac'])
					mat.node_tree.links.new(separate_rgb_node1.outputs['R'], mix_rgb_node2.inputs['Fac'])

					mat.node_tree.links.new(Tiling1TextureSampler_tex.outputs['Color'], mix_rgb_node1.inputs['Color1'])
					mat.node_tree.links.new(Tiling3TextureSampler_tex.outputs['Color'], mix_rgb_node1.inputs['Color2'])

					mat.node_tree.links.new(Tiling2TextureSampler_tex.outputs['Color'], mix_rgb_node2.inputs['Color1'])
					mat.node_tree.links.new(mix_rgb_node1.outputs['Color'], mix_rgb_node2.inputs['Color2'])

					mat.node_tree.links.new(mix_rgb_node2.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Base Color'])

					mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 1.0

				elif shader_type != "":
					print("DEBUG: shader type %s, used on material %s, still does not have its shading set." % (shader_type, mMaterialId))

				# AO map
				if shader_type.startswith("Vehicle") and "AoMapTextureSampler" in mat.node_tree.nodes:
					AoMapTextureSampler_tex = mat.node_tree.nodes['AoMapTextureSampler']
					mix_rgb_nodeAO = mat.node_tree.nodes.new(type='ShaderNodeMixRGB')
					color_ramp_node1 = mat.node_tree.nodes.new(type='ShaderNodeValToRGB')

					mix_rgb_nodeAO.blend_type = "OVERLAY"

					mat.node_tree.links.new(AoMapTextureSampler_tex.outputs['Color'], color_ramp_node1.inputs['Fac'])
					mat.node_tree.links.new(color_ramp_node1.outputs['Color'], mix_rgb_nodeAO.inputs['Color2'])

					if len(mat.node_tree.nodes[mMaterialId].inputs['Base Color'].links) > 0:
						node = mat.node_tree.nodes[mMaterialId].inputs['Base Color'].links[0].from_node
						mat.node_tree.links.new(node.outputs[0], mix_rgb_nodeAO.inputs['Color1'])
						mat.node_tree.links.new(mix_rgb_nodeAO.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Base Color'])
					else:
						mix_rgb_nodeAO.inputs['Fac'].default_value = mat.node_tree.nodes[mMaterialId].inputs['Base Color'].default_value
						if "mMaterialDiffuse" in parameters_Names or "materialDiffuse" in parameters_Names or "mGlassColour" in parameters_Names:
							pass
						else:
							pass
							# Not linking, avoiding problems
							mat.node_tree.links.new(mix_rgb_nodeAO.outputs['Color'], mat.node_tree.nodes[mMaterialId].inputs['Base Color'])

			# Untextured
			# Vehicle
			if shader_type == "Vehicle_Opaque_Reflective":
				mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 1.0
				mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 0.0
				mat.node_tree.nodes[mMaterialId].inputs['Transmission'].default_value = 0.0

				mat.use_screen_refraction = True
				mat.refraction_depth = 0.01

				mat.use_backface_culling = True

				bpy.context.scene.eevee.use_ssr = True
				bpy.context.scene.eevee.use_ssr_refraction = True

			# Track
			elif shader_type == "Cable_GreyScale_Doublesided":
				mat.node_tree.nodes[mMaterialId].inputs['Base Color'].default_value = (0.0, 0.0, 0.0, 1.0)
				mat.node_tree.nodes[mMaterialId].inputs['Metallic'].default_value = 0.4
				mat.node_tree.nodes[mMaterialId].inputs['Roughness'].default_value = 0.5


			# Properties
			mat["shader_type"] = shader_type
			mat["SamplerStateIds"] = [mSamplerStateId[0] for mSamplerStateId in sampler_states_info]
			for i in range(0, len(parameters_Names)):
				if not parameters_Names[i] in mat:
					mat[parameters_Names[i]] = parameters_Data[i][:]

				if parameters_Names[i] in ( 'DirtTint', 'materialDiffuse', 'LightmappedLightsGreenChannelColour', 'LightmappedLightsBlueChannelColour',
											'LightmappedLightsRedChannelColour', 'window_Tint', 'pearlescentColour', 'ReversingColour', 'UnusedColour',
											'mCrackedGlassSpecularColour', 'BrakeColour', 'RunningColour', 'mGlassColour', 'OverlayA_Diffuse', 'DiffuseB',
											'OverlayB_Diffuse', 'DiffuseA', 'Colour', 'gEmissiveColour', 'tiling1Diffuse', 'tiling3Diffuse', 'tiling2Diffuse',
											'decal_Diffuse', 'mMaterialDiffuse', 'Line_Diffuse', 'DiffuseColour', 'EmissiveColour', 'algaeColour', 'mExternalGlassColour'):
					property_manager = mat.id_properties_ui(parameters_Names[i])
					property_manager.update(subtype = 'COLOR')

			mat["is_shared_asset"] = is_shared_asset

	renderable_already_scene = []
	for renderable in renderables:
		mRenderableId = renderable[0]
		if mRenderableId in bpy.context.scene.objects:
			renderable_already_scene.append(mRenderableId)
			continue
		renderable_object = create_renderable(renderable, materials, shaders, resource_type)
		main_collection.objects.link(renderable_object)

		renderable_properties = renderable[1][1]
		object_center = renderable_properties[0]
		object_radius = renderable_properties[1]
		flags0 = renderable_properties[2]
		flags1 = renderable_properties[3]

		renderable_object["object_center"] = object_center
		renderable_object["object_radius"] = object_radius
		renderable_object["flags0"] = flags0
		renderable_object["flags1"] = flags1
		renderable_object["is_shared_asset"] = renderable[2]

	# Models
	for i in range(0, len(instances)):
		mModelId = instances[i][0]
		model_empty = bpy.data.objects.new(mModelId, None)
		if resource_type == "InstanceList":
			if i < (len(instances) - len(instances_dynamic)):
				instancelist_collection.objects.link(model_empty)
				mi16BackdropZoneID, unknown_0xC, mTransform_instance, is_instance_always_loaded = instances[i][1]
				model_empty["BackdropZoneID"] = mi16BackdropZoneID
				model_empty["unknown_0xC"] = unknown_0xC
				model_empty["unknown_0x8"] = unknown_0xC	# mw compatibility
				model_empty["is_always_loaded"] = is_instance_always_loaded
			else:
				dynamic_collection.objects.link(model_empty)
				unknown_0x44, muInstanceID, mTransform_instance, is_always_loaded, mWorldObjectId = instances[i][1]
				model_empty["unknown_0x44"] = unknown_0x44
				model_empty["InstanceID"] = muInstanceID
				#model_empty["Data"] = mpData
				model_empty["is_always_loaded"] = is_instance_always_loaded
				model_empty["WorldObjectId"] = mWorldObjectId
		elif resource_type == "GraphicsSpec":
			graphicsspec_collection.objects.link(model_empty)
		elif resource_type == "CharacterSpec":
			characterspec_collection.objects.link(model_empty)
		else:
			main_collection.objects.link(model_empty)

		model_empty["object_index"] = i
		model_empty.empty_display_size = 0.5

		model = models[mModelId]

		model_properties = model[1][1]
		mu8Flags, renderable_indices, lod_distances, has_tint_data, parameters_names, parameters_data, samplers_names, sampler_states, textures, unknown_0x25 = model_properties

		model_empty["Flags"] = mu8Flags
		model_empty["unknown_0x25"] = unknown_0x25
		model_empty["unknown_0x19"] = unknown_0x25
		model_empty["renderable_indices"] = renderable_indices
		model_empty["lod_distances"] = lod_distances
		model_empty["is_shared_asset"] = model[2]
		model_empty["model_has_tint_data"] = has_tint_data
		if parameters_names != []:
			for j in range(0, len(parameters_names)):
				model_empty["model_" + parameters_names[j]] = parameters_data[j][:]

		if samplers_names != []:
			model_empty["model_samplers_names"] = samplers_names
			model_empty["model_SamplerStateIds"] = sampler_states
			model_empty["model_TextureIds"] = textures

		for renderable_info in model[1][0]:
			mRenderableId = renderable_info[0]

			if len(renderable_info) == 2 and (mRenderableId not in renderable_already_scene):
				renderable_object = bpy.context.scene.objects[mRenderableId]

				renderable_index = renderable_info[1][0]
				renderable_object["renderable_index"] = renderable_index		#different models could use the same renderable with different properties

				renderable_object.parent = model_empty
				renderable_info.append("copied")
				if hide_low_lods == True:
					if renderable_index > 0:
						renderable_object.hide_set(True)
			else:
				src_renderable_object = bpy.data.objects.get(mRenderableId)
				src_renderable_mesh = bpy.data.meshes.get(mRenderableId)
				renderable_object = bpy.data.objects.new(mRenderableId, src_renderable_mesh)
				renderable_object.parent = model_empty
				main_collection.objects.link(renderable_object)

				renderable_index = renderable_info[1][0]

				#renderable_object["renderable_index"] = src_renderable_object["renderable_index"]
				renderable_object["renderable_index"] = renderable_index
				renderable_object["is_shared_asset"] = src_renderable_object["is_shared_asset"]
				renderable_object["flags0"] = src_renderable_object["flags0"]
				renderable_object["flags1"] = src_renderable_object["flags1"]
				renderable_object["object_center"] = src_renderable_object["object_center"]
				renderable_object["object_radius"] = src_renderable_object["object_radius"]

				hide_status = src_renderable_object.hide_get()
				renderable_object.hide_set(hide_status)

				if hide_low_lods == True:
					if renderable_index > 0:
						renderable_object.hide_set(True)

				for src_modifier in src_renderable_object.modifiers:
					modifier = renderable_object.modifiers.new(src_modifier.name, "NODES")
					try:
						bpy.data.node_groups.remove(modifier.node_group)
					except:
						pass
					modifier.node_group = src_modifier.node_group

			if resource_type == "InstanceList":
				hide_status = renderable_object.hide_get()
				renderable_object.users_collection[0].objects.unlink(renderable_object)
				#instancelist_collection.objects.link(renderable_object)
				if i < (len(instances) - len(instances_dynamic)):
					instancelist_collection.objects.link(renderable_object)
				else:
					dynamic_collection.objects.link(renderable_object)
				renderable_object.hide_set(hide_status)

			elif resource_type == "GraphicsSpec":
				hide_status = renderable_object.hide_get()
				renderable_object.users_collection[0].objects.unlink(renderable_object)
				graphicsspec_collection.objects.link(renderable_object)
				renderable_object.hide_set(hide_status)

			elif resource_type == "CharacterSpec":
				hide_status = renderable_object.hide_get()
				renderable_object.users_collection[0].objects.unlink(renderable_object)
				characterspec_collection.objects.link(renderable_object)
				renderable_object.hide_set(hide_status)

			renderable_objects.append(renderable_object)

			renderable_already_scene.append(mRenderableId)

		if resource_type == "InstanceList":
			mTransform = mTransform_instance
		else:
			mTransform = Matrix([[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0], [0.0, 0.0, 1.0, 0.0], [0.0, 0.0, 0.0, 1.0]]).transposed()
		model_empty.matrix_world = m @ mTransform
		# loss of precision on matrix_world: https://developer.blender.org/T30706

	for i in range(0, len(instances_wheel)):
		mModelId = instances_wheel[i][0]
		placement, is_spinnable, wheel_transform = instances_wheel[i][1]
		mWheelOffset, mWheelRotation, mWheelScale = wheel_transform

		model_empty = bpy.data.objects.new(mModelId, None)
		if resource_type == "GraphicsSpec":
			wheelgraphicspec_collection.objects.link(model_empty)
		else:
			main_collection.objects.link(model_empty)

		model_empty["object_index"] = i
		model_empty.empty_display_size = 0.5

		model = models[mModelId]

		model_properties = model[1][1]
		mu8Flags, renderable_indices, lod_distances, has_tint_data, parameters_names, parameters_data, samplers_names, sampler_states, textures, unknown_0x25 = model_properties

		model_empty["spinnable"] = is_spinnable
		model_empty["placement"] = placement
		model_empty["Flags"] = mu8Flags
		model_empty["unknown_0x25"] = unknown_0x25
		model_empty["unknown_0x19"] = unknown_0x25
		model_empty["renderable_indices"] = renderable_indices
		model_empty["lod_distances"] = lod_distances
		model_empty["is_shared_asset"] = model[2]
		model_empty["model_has_tint_data"] = has_tint_data
		if parameters_names != []:
			for j in range(0, len(parameters_names)):
				model_empty["model_" + parameters_names[j]] = parameters_data[j][:]

		if samplers_names != []:
			model_empty["model_samplers_names"] = samplers_names
			model_empty["model_SamplerStateIds"] = sampler_states
			model_empty["model_TextureIds"] = textures

		for renderable_info in model[1][0]:
			mRenderableId = renderable_info[0]

			if len(renderable_info) == 2 and (mRenderableId not in renderable_already_scene):
				renderable_object = bpy.context.scene.objects[mRenderableId]

				renderable_index = renderable_info[1][0]
				renderable_object["renderable_index"] = renderable_index		#different models could use the same renderable with different properties

				renderable_object.parent = model_empty
				renderable_info.append("copied")
				if hide_low_lods == True:
					if renderable_index > 0:
						renderable_object.hide_set(True)
			else:
				src_renderable_object = bpy.data.objects.get(mRenderableId)
				src_renderable_mesh = bpy.data.meshes.get(mRenderableId)
				renderable_object = bpy.data.objects.new(mRenderableId, src_renderable_mesh)
				renderable_object.parent = model_empty
				main_collection.objects.link(renderable_object)

				renderable_index = renderable_info[1][0]

				#renderable_object["renderable_index"] = src_renderable_object["renderable_index"]
				renderable_object["renderable_index"] = renderable_index
				renderable_object["is_shared_asset"] = src_renderable_object["is_shared_asset"]
				renderable_object["flags0"] = src_renderable_object["flags0"]
				renderable_object["flags1"] = src_renderable_object["flags1"]
				renderable_object["object_center"] = src_renderable_object["object_center"]
				renderable_object["object_radius"] = src_renderable_object["object_radius"]

				hide_status = src_renderable_object.hide_get()
				renderable_object.hide_set(hide_status)

				if hide_low_lods == True:
					if renderable_index > 0:
						renderable_object.hide_set(True)

				for src_modifier in src_renderable_object.modifiers:
					modifier = renderable_object.modifiers.new(src_modifier.name, "NODES")
					try:
						bpy.data.node_groups.remove(modifier.node_group)
					except:
						pass
					modifier.node_group = src_modifier.node_group

			if resource_type == "InstanceList":
				pass

			elif resource_type == "GraphicsSpec":
				hide_status = renderable_object.hide_get()
				renderable_object.users_collection[0].objects.unlink(renderable_object)
				wheelgraphicspec_collection.objects.link(renderable_object)
				renderable_object.hide_set(hide_status)

			renderable_already_scene.append(mRenderableId)

		mTransform = Matrix([[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0], [0.0, 0.0, 1.0, 0.0], [*mWheelOffset[0:3], 1.0]]).transposed()
		model_empty.matrix_world = m @ mTransform
		if "right" in placement.lower():
			model_empty.scale = [-1.0, 1.0, 1.0]
		# loss of precision on matrix_world: https://developer.blender.org/T30706

	if resource_type == "InstanceList" or resource_type == "GraphicsSpec" or resource_type == "CharacterSpec":
		for i, PolygonSoup in enumerate(PolygonSoups):
			if resource_type == "InstanceList":
				polygonsoup_empty_name = "PolygonSoup_%03d.%03d" % (i, track_unit_number)
			elif resource_type == "GraphicsSpec":
				polygonsoup_empty_name = "PolygonSoup_%03d.%03d" % (i, vehicle_name)
			polygonsoup_empty = bpy.data.objects.new(polygonsoup_empty_name, None)
			polygonsouplist_collection.objects.link(polygonsoup_empty)

			mabVertexOffsetMultiply, PolygonSoupVertices, PolygonSoupPolygons = PolygonSoup
			mfComprGranularity = 500/0x8000
			miVertexOffsetConstant = 500.0

			if resource_type == "InstanceList":
				polygonsoup_object_name = "PolygonSoupMesh_%03d.%03d" % (i, track_unit_number)
			elif resource_type == "GraphicsSpec":
				polygonsoup_object_name = "PolygonSoupMesh_%03d.%03d" % (i, vehicle_name)
			polygonsoup_object = create_polygonsoup(polygonsoup_object_name, PolygonSoupVertices, PolygonSoupPolygons, mabVertexOffsetMultiply, miVertexOffsetConstant, mfComprGranularity, resource_type, track_unit_number)
			polygonsoup_object.parent = polygonsoup_empty
			polygonsouplist_collection.objects.link(polygonsoup_object)

			#mTransform = Matrix([[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0], [0.0, 0.0, 1.0, 0.0], [*maiVertexOffsets, 1.0]]).transposed()
			mTransform = Matrix([[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0], [0.0, 0.0, 1.0, 0.0], [0.0, 0.0, 0.0, 1.0]]).transposed()
			#mTransform *= mfComprGranularity
			mTransform *= 1.0
			polygonsoup_empty.matrix_world = m @ mTransform

		# for i, sensor in enumerate(Skeleton):
			# sensor_index, mSensorPosition, mSensorRotation, parent_sensor, older_sensor, child_sensor, sensor_hash = sensor

			# if resource_type == "GraphicsSpec":
				# sensor_empty_name = "Sensor_%03d.%03d" % (sensor_index, vehicle_name)
			# elif resource_type == "CharacterSpec":
				# sensor_empty_name = "Sensor_%03d.%03d" % (sensor_index, character_name)
			# sensor_empty = bpy.data.objects.new(sensor_empty_name, None)
			# if resource_type == "GraphicsSpec":
				# sensor_empty.empty_display_type = 'SPHERE'
				# sensor_empty.empty_display_size = 0.025
				# sensor_empty.show_name = True
				# sensor_empty.show_in_front = True
			# elif resource_type == "CharacterSpec":
				# sensor_empty.empty_display_type = 'SPHERE'
				# sensor_empty.empty_display_size = 0.025
				# sensor_empty.show_name = False
				# sensor_empty.show_in_front = True
			# skeleton_collection.objects.link(sensor_empty)

			# sensor_empty["parent_sensor"] = parent_sensor
			# sensor_empty["correlated_sensor"] = older_sensor
			# sensor_empty["child_sensor"] = child_sensor
			# sensor_empty["sensor_hash"] = int_to_id(sensor_hash)

			# mTransform = Matrix([[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0], [0.0, 0.0, 1.0, 0.0], [*mSensorPosition, 1.0]]).transposed()
			# sensor_empty.matrix_world = m @ mTransform

		if len(Skeleton) > 0:
			cm_armature = bpy.data.armatures.new(mSkeletonId)
			cm_armature_rig = bpy.data.objects.new(mSkeletonId, cm_armature)
			skeleton_collection2.objects.link(cm_armature_rig)
			bpy.context.view_layer.objects.active = cm_armature_rig
			bpy.ops.object.mode_set(mode='EDIT', toggle=False)
			edit_bones = cm_armature_rig.data.edit_bones

			skeleton_method = "hinges"
			if skeleton_method == "joints":
				for i, sensor in enumerate(Skeleton):
					sensor_index, mSensorPosition, mSensorRotation, parent_sensor, older_sensor, child_sensor, has_ik, sensor_hash = sensor

					cm_bone_name = "Sensor_%03d" % sensor_index
					b = edit_bones.new(cm_bone_name)
					b.head = mSensorPosition
					#b.tail = mSensorPosition

					if parent_sensor != -1:
						b.parent = edit_bones["Sensor_%03d" % parent_sensor]
						b.use_connect = False
						#b.use_connect = True

						for sensor_ in Skeleton:
							if sensor_[0] == parent_sensor:
								#b.head = sensor_[1]
								b.tail = sensor_[1]
								break

					if b.length < 1e-3:
						b.tail = b.head + Vector([0.0, 0.0, 0.12])
						#b.head = b.tail + Vector([0.0, 0.0, 0.12])
					b["hash"] = int_to_id(sensor_hash)
					if has_ik == True:
						b["has_ik"] = has_ik

			elif skeleton_method == "hinges":
				for i, sensor in enumerate(Skeleton):
					sensor_index, mSensorPosition, mSensorRotation, parent_sensor, older_sensor, child_sensor, has_ik, sensor_hash = sensor

					cm_bone_name = "Sensor_%03d" % sensor_index
					b = edit_bones.new(cm_bone_name)
					b.head = mSensorPosition

					if parent_sensor != -1:
						b.parent = edit_bones["Sensor_%03d" % parent_sensor]
						b.use_connect = False
						#b.use_connect = True

						b.tail = Vector(mSensorPosition) + Vector([0.0, 0.2, 0.0])

						#for sensor_ in Skeleton:
						#	if sensor_[0] == parent_sensor:
						#		b.tail = Vector(mSensorPosition) + Vector([0.0, 0.2, 0.0])
						#		break

					if b.length < 1e-3:
						b.tail = b.head + Vector([0.0, 0.0, 0.12])
						#b.head = b.tail + Vector([0.0, 0.0, 0.12])
					b["hash"] = int_to_id(sensor_hash)
					if has_ik == True:
						b["has_ik"] = has_ik

			bpy.ops.object.mode_set(mode='OBJECT')
			mTransform = Matrix([[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0], [0.0, 0.0, 1.0, 0.0], [0.0, 0.0, 0.0, 1.0]]).transposed()
			cm_armature_rig.matrix_world = m @ mTransform
			cm_armature.display_type = 'WIRE'
			#cm_armature.show_names = True
			cm_armature.show_bone_custom_shapes = True
			cm_armature_rig.show_in_front = True

			# Bone shape
			try:
				bone_sphere = bpy.data.objects["dgi_sphere_skeleton"]
			except:
				bone_sphere = create_sphere(name="dgi_sphere_skeleton", radius=0.025)
				bone_sphere.use_fake_user = True

			for b in cm_armature_rig.pose.bones:
				b.custom_shape = bone_sphere
				b.use_custom_shape_bone_size = False

			for renderable_object in renderable_objects:
				modifier = renderable_object.modifiers.new(name=mSkeletonId, type='ARMATURE')
				modifier.object = cm_armature_rig

		if len(ControlMeshes) > 0:
			cm_armature = bpy.data.armatures.new(mControlMeshId)
			cm_armature_rig = bpy.data.objects.new(mControlMeshId, cm_armature)
			controlmesh_collection.objects.link(cm_armature_rig)
			bpy.context.view_layer.objects.active = cm_armature_rig
			bpy.ops.object.mode_set(mode='EDIT', toggle=False)
			edit_bones = cm_armature_rig.data.edit_bones

			for i, ControlMesh in enumerate(ControlMeshes):
				cm_index, cm_coordinates_A, cm_coordinates_B, cm_limit = ControlMesh
				#cm_bone_name = "ControlMesh_%03d.%03d" % (cm_index, vehicle_name)
				cm_bone_name = "Bone_%03d" % cm_index
				b = edit_bones.new(cm_bone_name)
				b.head = cm_coordinates_A
				b.tail = cm_coordinates_B

				if b.length < 1e-3:
					b.tail = b.head + Vector([0.0, 0.0, 0.12])

				b["Limit"] = cm_limit

			bpy.ops.object.mode_set(mode='OBJECT')
			mTransform = Matrix([[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0], [0.0, 0.0, 1.0, 0.0], [0.0, 0.0, 0.0, 1.0]]).transposed()
			cm_armature_rig.matrix_world = m @ mTransform
			cm_armature.display_type = 'WIRE'
			#cm_armature.show_names = True
			cm_armature.show_bone_custom_shapes = True
			cm_armature_rig.show_in_front = True

			# Bone shape
			try:
				bone_sphere = bpy.data.objects["dgi_sphere_controlmesh"]
			except:
				bone_sphere = create_sphere(name="dgi_sphere_controlmesh", radius=0.025)
				bone_sphere.use_fake_user = True

			for b in cm_armature_rig.pose.bones:
				b.custom_shape = bone_sphere
				b.use_custom_shape_bone_size = False

			for renderable_object in renderable_objects:
				modifier = renderable_object.modifiers.new(name=mControlMeshId, type='ARMATURE')
				modifier.object = cm_armature_rig

		for i, LightObject in enumerate(lights):
			light_empty_name = "Light_%03d.%03d" % (i, track_unit_number)
			light_data = bpy.data.lights.new(name = light_empty_name, type = 'POINT')
			light_data.energy = 1000
			light_empty = bpy.data.objects.new(light_empty_name, light_data)
			lightinstancelist_collection.objects.link(light_empty)

			muInstanceID, mTransform_light, is_light_always_loaded, mLightObjectId = LightObject[1]
			light_empty["InstanceID"] = muInstanceID
			light_empty["is_always_loaded"] = is_light_always_loaded
			light_empty["LightObjectId"] = mLightObjectId

			light_empty.matrix_world = m @ mTransform_light

	elif resource_type == "PolygonSoupList":
		for collision in world_collision:
			track_unit_number, mPolygonSoupList, PolygonSoups, polygonsouplist_collection = collision
			for i, PolygonSoup in enumerate(PolygonSoups):
				if track_unit_number != None:
					polygonsoup_empty_name = "PolygonSoup_%03d.%03d" % (i, track_unit_number)
				else:
					polygonsoup_empty_name = "PolygonSoup_%03d" % i
				polygonsoup_empty = bpy.data.objects.new(polygonsoup_empty_name, None)
				polygonsouplist_collection.objects.link(polygonsoup_empty)

				mabVertexOffsetMultiply, PolygonSoupVertices, PolygonSoupPolygons = PolygonSoup
				mfComprGranularity = 500/0x8000
				miVertexOffsetConstant = 500.0

				if track_unit_number != None:
					polygonsoup_object_name = "PolygonSoupMesh_%03d.%03d" % (i, track_unit_number)
				else:
					polygonsoup_object_name = "PolygonSoupMesh_%03d" % i
				polygonsoup_object = create_polygonsoup(polygonsoup_object_name, PolygonSoupVertices, PolygonSoupPolygons, mabVertexOffsetMultiply, miVertexOffsetConstant, mfComprGranularity, resource_type, track_unit_number)
				polygonsoup_object.parent = polygonsoup_empty
				polygonsouplist_collection.objects.link(polygonsoup_object)

				#mTransform = Matrix([[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0], [0.0, 0.0, 1.0, 0.0], [*maiVertexOffsets, 1.0]]).transposed()
				mTransform = Matrix([[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0], [0.0, 0.0, 1.0, 0.0], [0.0, 0.0, 0.0, 1.0]]).transposed()
				#mTransform *= mfComprGranularity
				mTransform *= 1.0
				polygonsoup_empty.matrix_world = m @ mTransform

	elif resource_type == "TriggerData":
		BoxTriggers, SphereTriggers, LocatorTriggers, CellTriggers = triggers
		for BoxTrigger in BoxTriggers:
			trigger_index, super_Trigger, mRotation, mDimension = BoxTrigger
			mPosition, miOwnerId, meTriggerType, meTriggerShape, mxFlags, miPad1 = super_Trigger

			trigger_empty_name = "BoxTrigger_%03d" % (trigger_index)
			trigger_empty = bpy.data.objects.new(trigger_empty_name, None)
			if meTriggerShape == 'E_TRIGGERSHAPE_BOX':
				trigger_empty.empty_display_type = 'CUBE'
			elif meTriggerShape == 'E_TRIGGERSHAPE_SPHERE':
				trigger_empty.empty_display_type = 'SPHERE'
			elif meTriggerShape == 'E_TRIGGERSHAPE_LOCATOR':
				trigger_empty.empty_display_type = 'SINGLE_ARROW'
			elif meTriggerShape == 'E_TRIGGERSHAPE_COUNT':
				trigger_empty.empty_display_type = 'PLAIN_AXES'
			elif meTriggerShape == 'E_TRIGGERSHAPE_INVALID':
				trigger_empty.empty_display_type = 'PLAIN_AXES'
			else:
				pass

			boxtrigger_collection.objects.link(trigger_empty)
			mDimension = [DimensionTrigger*0.5 for DimensionTrigger in mDimension]
			mTransform = Matrix.LocRotScale(mPosition, Quaternion(mRotation), mDimension)
			trigger_empty.matrix_world = m @ mTransform

			trigger_empty["OwnerId"] = miOwnerId
			trigger_empty["TriggerType"] = meTriggerType
			trigger_empty["TriggerShape"] = meTriggerShape
			trigger_empty["Flags"] = mxFlags

		for SphereTrigger in SphereTriggers:
			trigger_index, super_Trigger, mfRadius = SphereTrigger
			mPosition, miOwnerId, meTriggerType, meTriggerShape, mxFlags, miPad1 = super_Trigger

			trigger_empty_name = "SphereTrigger_%03d" % (trigger_index)
			trigger_empty = bpy.data.objects.new(trigger_empty_name, None)
			#trigger_empty.empty_display_type = 'SPHERE'
			if meTriggerShape == 'E_TRIGGERSHAPE_BOX':
				trigger_empty.empty_display_type = 'CUBE'
			elif meTriggerShape == 'E_TRIGGERSHAPE_SPHERE':
				trigger_empty.empty_display_type = 'SPHERE'
			elif meTriggerShape == 'E_TRIGGERSHAPE_LOCATOR':
				trigger_empty.empty_display_type = 'SINGLE_ARROW'
			elif meTriggerShape == 'E_TRIGGERSHAPE_COUNT':
				trigger_empty.empty_display_type = 'PLAIN_AXES'
			elif meTriggerShape == 'E_TRIGGERSHAPE_INVALID':
				trigger_empty.empty_display_type = 'PLAIN_AXES'
			else:
				pass
			trigger_empty.empty_display_size = mfRadius*2.0
			spheretrigger_collection.objects.link(trigger_empty)

			mTransform = Matrix([[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0], [0.0, 0.0, 1.0, 0.0], [*mPosition, 1.0]]).transposed()
			trigger_empty.matrix_world = m @ mTransform

			trigger_empty["OwnerId"] = miOwnerId
			trigger_empty["TriggerType"] = meTriggerType
			trigger_empty["TriggerShape"] = meTriggerShape
			trigger_empty["Flags"] = mxFlags

		for LocatorTrigger in LocatorTriggers:
			trigger_index, super_Trigger, mDirection = LocatorTrigger
			mPosition, miOwnerId, meTriggerType, meTriggerShape, mxFlags, miPad1 = super_Trigger

			trigger_empty_name = "LocatorTrigger_%03d" % (trigger_index)
			trigger_empty = bpy.data.objects.new(trigger_empty_name, None)
			if meTriggerShape == 'E_TRIGGERSHAPE_BOX':
				trigger_empty.empty_display_type = 'CUBE'
			elif meTriggerShape == 'E_TRIGGERSHAPE_SPHERE':
				trigger_empty.empty_display_type = 'SPHERE'
			elif meTriggerShape == 'E_TRIGGERSHAPE_LOCATOR':
				trigger_empty.empty_display_type = 'SINGLE_ARROW'
			elif meTriggerShape == 'E_TRIGGERSHAPE_COUNT':
				trigger_empty.empty_display_type = 'PLAIN_AXES'
			elif meTriggerShape == 'E_TRIGGERSHAPE_INVALID':
				trigger_empty.empty_display_type = 'PLAIN_AXES'
			else:
				pass
			locatortrigger_collection.objects.link(trigger_empty)

			mTransform = Matrix.LocRotScale(mPosition, Euler(mDirection), None)
			trigger_empty.matrix_world = m @ mTransform

			trigger_empty["OwnerId"] = miOwnerId
			trigger_empty["TriggerType"] = meTriggerType
			trigger_empty["TriggerShape"] = meTriggerShape
			trigger_empty["Flags"] = mxFlags

	elif resource_type == "ZoneList":
		district_color = {}
		for zone in zonelist:
			muZoneId, [mauNeighbourId, mauNeighbourFlags, muDistrictId, miZoneType, muArenaId, miNumSafeNeighbours], zonepoints = zone
			try:
				RGBA_random_district = district_color[muDistrictId]
			except:
				RGBA_random_district = get_random_color()
				district_color[muDistrictId] = RGBA_random_district

			zone_object = create_zone(muZoneId, zonepoints, muDistrictId, RGBA_random_district, resource_version)

			mTransform = Matrix([[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0], [0.0, 0.0, 1.0, 0.0], [0.0, 0.0, 0.0, 1.0]]).transposed()

			zone_object.matrix_world = m @ mTransform
			zone_object.show_wire = True
			zone_object.color = RGBA_random_district
			if mauNeighbourId != []:
				zone_object["NeighbourIds"] = mauNeighbourId
				zone_object["NeighbourFlags"] = mauNeighbourFlags
			#zone_object["DistrictId"] = muDistrictId
			zone_object["ZoneType"] = miZoneType
			zone_object["ArenaId"] = muArenaId
			zone_object["unknown_0x40"] = miNumSafeNeighbours
			zone_object["NumSafeNeighbours"] = miNumSafeNeighbours

			zonelist_collection.objects.link(zone_object)


	#if len(instances_effects) > 0:
	for effect_instance in instances_effects:
		EffectId, i, effectsLocation, EffectData = effect_instance

		effect_object_name = "Effect_%d.%s" % (i, vehicle_name)
		effect_empty = bpy.data.objects.new(effect_object_name, None)
		effects_collection.objects.link(effect_empty)

		effect_empty['EffectId'] = EffectId

		effect_empty.matrix_world = m @ effect_empty.matrix_world

		for j, effectLocation in enumerate(effectsLocation):
			effect_object_name2 = "Effect_%d_copy_%d.%s" % (i, j, vehicle_name)
			effect_empty2 = bpy.data.objects.new(effect_object_name2, None)
			effect_empty2.parent = effect_empty

			mLocatorMatrix = Matrix([[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0], [0.0, 0.0, 1.0, 0.0], [*effectLocation[0], 1.0]]).transposed()
			effect_empty2.matrix_world = m @ mLocatorMatrix
			effect_empty2.rotation_mode = 'QUATERNION'
			effect_empty2.rotation_quaternion = [effectLocation[1][3], effectLocation[1][0], effectLocation[1][1], effectLocation[1][2]]

			effect_empty2.empty_display_type = 'SINGLE_ARROW'
			effect_empty2.empty_display_size = 0.5

			if EffectData != []:
				effect_empty2['sensor_hash'] = int_to_id(EffectData[j])

			effects_collection.objects.link(effect_empty2)

	if len(instance_character) > 0:
		# Creating driver object
		mCharacterSpecID, characterOffset = instance_character

		driver_object_name = "%s_Driver" % (vehicle_name)
		driver_empty = bpy.data.objects.new(driver_object_name, None)
		#driver_empty["CharacterSpecID"] = mCharacterSpecID

		character_collection.objects.link(driver_empty)

		# if os.path.isfile(characterLibrary) == True:
			# with bpy.data.libraries.load(characterLibrary, link=False) as (data_from, data_to):
				# data_to.collections = [col for col in data_from.collections if col.startswith(str(mCharacterSpecID))]
				# if data_to.collections == []:
					# data_to.collections = [[col for col in data_from.collections if col.endswith("Character")][0]]

			# for library_collection in data_to.collections:
				# driver_objects = library_collection.objects
				# for driver_object in driver_objects:
					# if driver_object.type == "ARMATURE":
						# character_collection.objects.link(driver_object)
						# mLocatorMatrix = Matrix([[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0], [0.0, 0.0, 1.0, 0.0], [*characterOffset, 1.0]]).transposed()
						# driver_object.matrix_world = m @ mLocatorMatrix
						# driver_object.hide_set(True)
					# else:
						# for child in driver_object.children:
							# if child["renderable_index"] == 0:
								# child.parent = driver_empty
								# character_collection.objects.link(child)
								# break

		mLocatorMatrix = Matrix([[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0], [0.0, 0.0, 1.0, 0.0], [*characterOffset, 1.0]]).transposed()
		# x + 0.36

		driver_empty.matrix_world = m @ mLocatorMatrix

	elapsed_time = time.time() - importing_time
	print("... %.4fs" % elapsed_time)

	## Adjusting scene
	for window in bpy.context.window_manager.windows:
		for area in window.screen.areas:
			if area.type == 'VIEW_3D':
				for space in area.spaces:
					if space.type == 'VIEW_3D':
						if resource_type == "PolygonSoupList":
							space.shading.type = 'SOLID'
						else:
							space.shading.type = 'SOLID'
							space.shading.color_type = 'VERTEX'
							space.shading.light = 'FLAT'

							space.shading.type = 'MATERIAL'
						space.clip_end = 100000
				region = next(region for region in area.regions if region.type == 'WINDOW')
				override = bpy.context.copy()
				override['area'] = area
				override['region'] = region
				bpy.ops.view3d.view_all(override, use_all_regions=False, center=False)

	if is_bundle == True:
		temp_dir.cleanup()

	print("Finished")
	elapsed_time = time.time() - start_time
	print("Elapsed time: %.4fs" % elapsed_time)
	return {'FINISHED'}


def read_vehiclelist(vehiclelist_path, resource_version):
	if resource_version == "NFSHPR_PC":
		data_format = ("<Q", 0x8)
		vehiclelistentry_length = 0x70
	elif resource_version == "NFSHP_PC":
		data_format = ("<I", 0x4)
		vehiclelistentry_length = 0x60

	VehicleList = []
	with open(vehiclelist_path, "rb") as f:
		miVersionNumber = struct.unpack("<i", f.read(0x4))[0]
		muNumVehicles = struct.unpack("<I", f.read(0x4))[0]
		muNumManufacturers = struct.unpack("<I", f.read(0x4))[0]
		if resource_version == "NFSHPR_PC":
			mu4BytePad = f.read(0x4)
		mpEntries = struct.unpack(data_format[0], f.read(data_format[1]))[0]
		mpManufacturerEntries = struct.unpack(data_format[0], f.read(data_format[1]))[0]
		if resource_version == "NFSHPR_PC":
			mu16BytePad = f.read(0x10)
		elif resource_version == "NFSHP_PC":
			mu12BytePad = f.read(0xC)

		f.seek(mpEntries, 0)
		if miVersionNumber == 1016:
			for i in range(0, muNumVehicles):
				f.seek(mpEntries + vehiclelistentry_length*i, 0)

				mId = struct.unpack("<i", f.read(0x4))[0]
				mNameId = struct.unpack("<i", f.read(0x4))[0]
				mDescriptionId = struct.unpack("<i", f.read(0x4))[0]
				Tagline = struct.unpack("<i", f.read(0x4))[0]
				mShortNameId = struct.unpack("<i", f.read(0x4))[0]
				mManufacturerId = struct.unpack("<i", f.read(0x4))[0]
				DriveTrain = struct.unpack("<i", f.read(0x4))[0]
				EngineType = struct.unpack("<i", f.read(0x4))[0]
				mSelectionImageId = struct.unpack("<i", f.read(0x4))[0]
				mNameImageId = struct.unpack("<i", f.read(0x4))[0]
				CarSelectSound = struct.unpack("<i", f.read(0x4))[0]
				dlc = struct.unpack("<i", f.read(0x4))[0]
				mfRealWorldTopSpeedMph = struct.unpack("<f", f.read(0x4))[0]
				mfTopSpeedBonusMph = struct.unpack("<f", f.read(0x4))[0]
				#mfHandlingTopSpeedMph = struct.unpack("<f", f.read(0x4))[0]
				_ = struct.unpack("<i", f.read(0x4))[0]
				mfAcceleration = struct.unpack("<f", f.read(0x4))[0]
				NumberProduced = struct.unpack("<i", f.read(0x4))[0]
				miPrice = struct.unpack("<i", f.read(0x4))[0]
				miPower = struct.unpack("<i", f.read(0x4))[0]
				miPowerRPM = struct.unpack("<i", f.read(0x4))[0]
				miYear = struct.unpack("<i", f.read(0x4))[0]
				Weight = struct.unpack("<i", f.read(0x4))[0]
				mxFlags = struct.unpack("<i", f.read(0x4))[0]
				_ = struct.unpack("<B", f.read(0x1))[0]
				padding = f.read(0x3)
				miTier = struct.unpack("<h", f.read(0x2))[0]
				padding = f.read(0xE)

				mName = get_vehicle_name(mId)
				DriveTrain = get_drivetrain_type(DriveTrain)
				EngineType = get_engine_type(EngineType)
				mFlags = get_vehicle_flag(mxFlags)
				miTier = get_tier_type(miTier)
				dlc = get_DLC_type(dlc)

				if mFlags == 'E_VEHICLE_FLAG_COP':
					mName += " (Cop)"
				elif mxFlags % 2 != 0:
					mName += " (Cop)"

				VehicleList.append((str(mId), mName, str(mId)))

		elif miVersionNumber == 1015:
			for i in range(0, muNumVehicles):
				f.seek(mpEntries + vehiclelistentry_length*i, 0)

				mId = struct.unpack("<i", f.read(0x4))[0]
				mNameId = struct.unpack("<i", f.read(0x4))[0]
				mDescriptionId = struct.unpack("<i", f.read(0x4))[0]
				Tagline = struct.unpack("<i", f.read(0x4))[0]
				mShortNameId = struct.unpack("<i", f.read(0x4))[0]
				mManufacturerId = struct.unpack("<i", f.read(0x4))[0]
				DriveTrain = struct.unpack("<i", f.read(0x4))[0]
				EngineType = struct.unpack("<i", f.read(0x4))[0]
				mSelectionImageId = struct.unpack("<i", f.read(0x4))[0]
				mNameImageId = struct.unpack("<i", f.read(0x4))[0]
				mfRealWorldTopSpeedMph = struct.unpack("<f", f.read(0x4))[0]
				mfHandlingTopSpeedMph = struct.unpack("<f", f.read(0x4))[0]
				_ = struct.unpack("<i", f.read(0x4))[0]
				mfAcceleration = struct.unpack("<f", f.read(0x4))[0]
				NumberProduced = struct.unpack("<i", f.read(0x4))[0]
				miPrice = struct.unpack("<i", f.read(0x4))[0]
				miPower = struct.unpack("<i", f.read(0x4))[0]
				miPowerRPM = struct.unpack("<i", f.read(0x4))[0]
				miYear = struct.unpack("<i", f.read(0x4))[0]
				Weight = struct.unpack("<i", f.read(0x4))[0]
				mxFlags = struct.unpack("<i", f.read(0x4))[0]
				_ = struct.unpack("<B", f.read(0x1))[0]
				padding = f.read(0x3)
				miTier = struct.unpack("<h", f.read(0x2))[0]
				padding = f.read(0x2)
				CarSelectSound = struct.unpack("<i", f.read(0x4))[0]

				mName = get_vehicle_name(mId)
				DriveTrain = get_drivetrain_type(DriveTrain)
				EngineType = get_engine_type(EngineType)
				mFlags = get_vehicle_flag(mxFlags)
				miTier = get_tier_type(miTier)

				#if mFlags == 'E_VEHICLE_FLAG_COP':
				#	mName += " (Cop)"
				#elif mxFlags % 2 != 0:
				#	mName += " (Cop)"

				VehicleList.append((str(mId), mName, str(mId)))

		f.seek(mpManufacturerEntries, 0)
		for i in range(0, muNumManufacturers):
			f.seek(mpManufacturerEntries + 0x10*i, 0)

			mId = struct.unpack("<i", f.read(0x4))[0]
			mNameStringId = struct.unpack("<i", f.read(0x4))[0]
			mCountryId = struct.unpack("<i", f.read(0x4))[0]
			mSelectionImageId = struct.unpack("<i", f.read(0x4))[0]

			mCountryId = get_country_type(mCountryId)

	return VehicleList


def read_instancelist(instancelist_path, resource_version): # OK
	if resource_version == "NFSHPR_PC":
		data_format = ("<Q", 0x8)
		instance_length = 0x60
	elif resource_version == "NFSHP_PC":
		data_format = ("<I", 0x4)
		instance_length = 0x50

	instances = []
	all_parameters_names = []
	with open(instancelist_path, "rb") as f:
		mpaInstances = struct.unpack(data_format[0], f.read(data_format[1]))[0]
		muArraySize, muNumInstances, muVersionNumber = struct.unpack("<III", f.read(0xC))

		if os.path.getsize(instancelist_path) <= 0x20:
			muImportCount = 0
			muImportOffset = 0
		else:
			f.seek(os.path.getsize(instancelist_path) - 0x8, 0)
			check = struct.unpack("<I", f.read(0x4))[0]
			count = 1
			while check != mpaInstances:
				f.seek(-0x14, 1)
				check = struct.unpack("<I", f.read(0x4))[0]
				count = count + 1
			muImportCount = count
			muImportOffset = os.path.getsize(instancelist_path) - muImportCount*0x10


		for i in range(0, muArraySize):
			f.seek(mpaInstances + instance_length*i, 0)

			mpModel = struct.unpack(data_format[0], f.read(data_format[1]))[0]	# q on HPR
			mi16BackdropZoneID, mu16Pad, unknown_0xC = struct.unpack("<hHI", f.read(0x8))
			unknown_0x10 = struct.unpack("<i", f.read(0x4))
			if resource_version == "NFSHPR_PC":
				unknown_0x14, unknown_0x18, unknown_0x1C = struct.unpack("<iii", f.read(0xC))	# padding
			mTransform = [[*struct.unpack("<4f", f.read(0x10))],[*struct.unpack("<4f", f.read(0x10))],[*struct.unpack("<4f", f.read(0x10))],[*struct.unpack("<4f", f.read(0x10))]]
			mTransform = Matrix(mTransform)
			mTransform = mTransform.transposed()

			f.seek(muImportOffset + 0x10*i, 0)
			mModelId = bytes_to_id(f.read(0x4))

			is_always_loaded = True
			if i >= muNumInstances:
				is_always_loaded = False

			instance_properties = [mi16BackdropZoneID, unknown_0xC, mTransform, is_always_loaded]
			instances.append([mModelId, instance_properties])

	return instances


def read_dynamicinstancelist(dynamicinstancelist_path, worldobject_dir, shared_worldobject_dir, resource_version): #ok
	if resource_version == "NFSHPR_PC":
		data_format = ("<Q", 0x8)
		instance_length = 0x60
	elif resource_version == "NFSHP_PC":
		data_format = ("<I", 0x4)
		instance_length = 0x50

	instances = []
	with open(dynamicinstancelist_path, "rb") as f:
		muVersionNumber = struct.unpack(data_format[0], f.read(data_format[1]))[0]
		mpaInstances = struct.unpack(data_format[0], f.read(data_format[1]))[0]
		muArraySize = struct.unpack(data_format[0], f.read(data_format[1]))[0]
		unknown_0xC = struct.unpack(data_format[0], f.read(data_format[1]))[0]

		if os.path.getsize(dynamicinstancelist_path) <= 0x20:
			muImportCount = 0
			muImportOffset = 0
		else:
			f.seek(os.path.getsize(dynamicinstancelist_path) - 0x8, 0)
			check = struct.unpack("<I", f.read(0x4))[0]
			count = 1
			while check != (mpaInstances + 0x40):
				f.seek(-0x14, 1)
				check = struct.unpack("<I", f.read(0x4))[0]
				count = count + 1
			muImportCount = count
			muImportOffset = os.path.getsize(dynamicinstancelist_path) - muImportCount*0x10

		for i in range(0, muArraySize):
			f.seek(mpaInstances + instance_length*i, 0)

			mTransform = [[*struct.unpack("<4f", f.read(0x10))],[*struct.unpack("<4f", f.read(0x10))],[*struct.unpack("<4f", f.read(0x10))],[*struct.unpack("<4f", f.read(0x10))]]
			mTransform = Matrix(mTransform)
			mTransform = mTransform.transposed()

			mpWorldObject = struct.unpack(data_format[0], f.read(data_format[1]))[0]	# q on HPR
			unknown_0x44, muInstanceID, unknown_0x50 = struct.unpack("<fIi", f.read(0xC))
			# others are padding

			#f.seek(-muArraySize*0x10 + 0x10*i, 2)
			f.seek(muImportOffset + 0x10*i, 0)
			mWorldObjectId = bytes_to_id(f.read(0x4))

			worldobject_path = os.path.join(worldobject_dir, mWorldObjectId + ".dat")
			if not os.path.isfile(worldobject_path):
				worldobject_path = os.path.join(shared_worldobject_dir, mWorldObjectId + ".dat")
				is_shared_asset = True
				if not os.path.isfile(worldobject_path):
					print("WARNING: failed to open world object %s: no such file in '%s' and '%s'." % (mWorldObjectId, worldobject_dir, shared_worldobject_dir))
					continue
			mModelId = read_worldobject(worldobject_path)

			is_always_loaded = True
			instance_properties = [unknown_0x44, muInstanceID, mTransform, is_always_loaded, mWorldObjectId]
			instances.append([mModelId, instance_properties])

	return instances


def read_worldobject(worldobject_path): #ok
	mModelId = ""
	with open(worldobject_path, "rb") as f:
		f.seek(os.path.getsize(worldobject_path) - 0x8, 0)
		check = struct.unpack("<I", f.read(0x4))[0]
		count = 1
		while check != 0x8:
			f.seek(-0x14, 1)
			check = struct.unpack("<I", f.read(0x4))[0]
			count = count + 1
		muImportCount = count
		muImportOffset = os.path.getsize(worldobject_path) - muImportCount*0x10

		f.seek(muImportOffset, 0)
		mModelId = bytes_to_id(f.read(0x4))
		_ = struct.unpack("<i", f.read(0x4))[0]
		muOffset = struct.unpack("<I", f.read(0x4))[0]
		padding = struct.unpack("<i", f.read(0x4))[0]

	return mModelId


def read_lightinstancelist(lightinstancelist_path, resource_version): #ok
	if resource_version == "NFSHPR_PC":
		data_format = ("<Q", 0x8)
		instance_length = 0x70
	elif resource_version == "NFSHP_PC":
		data_format = ("<I", 0x4)
		instance_length = 0x60

	lights = []
	with open(lightinstancelist_path, "rb") as f:
		muVersionNumber = struct.unpack(data_format[0], f.read(data_format[1]))[0]
		mpaInstances = struct.unpack(data_format[0], f.read(data_format[1]))[0]
		muArraySize = struct.unpack(data_format[0], f.read(data_format[1]))[0]
		unknown_0xC = struct.unpack(data_format[0], f.read(data_format[1]))[0]

		if os.path.getsize(lightinstancelist_path) <= 0x20:
			muImportCount = 0
			muImportOffset = 0
		else:
			f.seek(os.path.getsize(lightinstancelist_path) - 0x8, 0)
			check = struct.unpack("<H", f.read(0x2))[0]
			count = 1
			while check != (mpaInstances + 0x40):
				f.seek(-0x12, 1)
				check = struct.unpack("<H", f.read(0x2))[0]
				count = count + 1
			muImportCount = count
			muImportOffset = os.path.getsize(lightinstancelist_path) - muImportCount*0x10

		for i in range(0, muArraySize):
			f.seek(mpaInstances + instance_length*i, 0)
			mTransform = [[*struct.unpack("<4f", f.read(0x10))],[*struct.unpack("<4f", f.read(0x10))],[*struct.unpack("<4f", f.read(0x10))],[*struct.unpack("<4f", f.read(0x10))]]
			mTransform = Matrix(mTransform)
			mTransform = mTransform.transposed()

			mpLightObject = struct.unpack(data_format[0], f.read(data_format[1]))[0]	# q on HPR
			unknown_0x44 = struct.unpack(data_format[0], f.read(data_format[1]))[0]
			unknown_0x48 = struct.unpack(data_format[0], f.read(data_format[1]))[0]
			unknown_0x4C = struct.unpack(data_format[0], f.read(data_format[1]))[0]

			unknown_0x50, muInstanceID, unknown_0x58, unknown_0x5C = struct.unpack("<iIii", f.read(0x10))

			#f.seek(-muArraySize*0x10 + 0x10*i, 2)
			f.seek(muImportOffset + 0x10*i, 0)
			mLightObjectId = bytes_to_id(f.read(0x4))

			is_always_loaded = True
			lights_properties = [muInstanceID, mTransform, is_always_loaded, mLightObjectId]
			lights.append([mLightObjectId, lights_properties])

	return lights


def read_polygonsouplist(polygonsouplist_path, resource_version): #ok
	if resource_version == "NFSHPR_PC":
		data_format = ("<Q", 0x8)
	elif resource_version == "NFSHP_PC":
		data_format = ("<I", 0x4)

	PolygonSoups = []
	if os.path.isfile(polygonsouplist_path) == True:
		with open(polygonsouplist_path, "rb") as f:
			mMin = struct.unpack("<3f", f.read(0xC))
			mMin_w = struct.unpack("<f", f.read(0x4))[0]
			mMax = struct.unpack("<3f", f.read(0xC))
			mMax_w = struct.unpack("<f", f.read(0x4))[0]
			mpapPolySoups = struct.unpack(data_format[0], f.read(data_format[1]))[0]
			mpaPolySoupBoxes = struct.unpack(data_format[0], f.read(data_format[1]))[0]
			miNumPolySoups = struct.unpack("<i", f.read(0x4))[0]
			miDataSize = struct.unpack("<i", f.read(0x4))[0]

			mpPolySoups = []
			f.seek(mpapPolySoups, 0)
			if resource_version == "NFSHPR_PC":
				mpPolySoups = struct.unpack("<%dQ" % miNumPolySoups, f.read(0x8*miNumPolySoups))
			elif resource_version == "NFSHP_PC":
				mpPolySoups = struct.unpack("<%dI" % miNumPolySoups, f.read(0x4*miNumPolySoups))

			PolySoupBoxes = []
			f.seek(mpaPolySoupBoxes, 0)
			for i in range(0, miNumPolySoups):
				f.seek(int(mpaPolySoupBoxes + 0x70*(i//4) + 0x4*(i%4)), 0)
				mAabbMinX = struct.unpack("<f", f.read(0x4))[0]
				f.seek(0xC, 1)
				mAabbMinY = struct.unpack("<f", f.read(0x4))[0]
				f.seek(0xC, 1)
				mAabbMinZ = struct.unpack("<f", f.read(0x4))[0]
				f.seek(0xC, 1)
				mAabbMaxX = struct.unpack("<f", f.read(0x4))[0]
				f.seek(0xC, 1)
				mAabbMaxY = struct.unpack("<f", f.read(0x4))[0]
				f.seek(0xC, 1)
				mAabbMaxZ = struct.unpack("<f", f.read(0x4))[0]
				f.seek(0xC, 1)
				mValidMasks = struct.unpack("<i", f.read(0x4))[0]
				PolySoupBoxes.append([[mAabbMinX, mAabbMinY, mAabbMinZ], [mAabbMaxX, mAabbMaxY, mAabbMaxZ], mValidMasks])

			for i in range(0, miNumPolySoups):
				f.seek(mpPolySoups[i], 0)
				mpaPolygons = struct.unpack(data_format[0], f.read(data_format[1]))[0]
				mpaVertices = struct.unpack(data_format[0], f.read(data_format[1]))[0]
				mu16DataSize = struct.unpack("<H", f.read(0x2))[0]		# DataSize plus padding previous PolySoup
				mabVertexOffsetMultiply = struct.unpack("<3b", f.read(0x3))
				mu8NumQuads = struct.unpack("<B", f.read(0x1))[0]
				mu8TotalNumPolys = struct.unpack("<B", f.read(0x1))[0]
				mu8NumVertices = struct.unpack("<B", f.read(0x1))[0]

				PolygonSoupVertices = []
				f.seek(mpaVertices, 0)
				for j in range(0, mu8NumVertices):
					mu16X, mu16Y, mu16Z = struct.unpack("<HHH", f.read(0x6))
					PolygonSoupVertex = [mu16X, mu16Y, mu16Z]
					PolygonSoupVertices.append(PolygonSoupVertex)

				PolygonSoupPolygons = []
				f.seek(mpaPolygons, 0)
				for j in range(0, mu8NumQuads):
					mu16CollisionTag_part0 = struct.unpack("<H", f.read(0x2))[0]
					mu16CollisionTag_part1 = struct.unpack("<H", f.read(0x2))[0]
					mau8VertexIndices = struct.unpack("<4B", f.read(0x4))
					mau8EdgeCosines = struct.unpack("<4B", f.read(0x4))
					PolygonSoupPolygons.append([[mu16CollisionTag_part0, mu16CollisionTag_part1], mau8VertexIndices, mau8EdgeCosines])

				for j in range(mu8NumQuads, mu8TotalNumPolys):
					mu16CollisionTag_part0 = struct.unpack("<H", f.read(0x2))[0]
					mu16CollisionTag_part1 = struct.unpack("<H", f.read(0x2))[0]
					mau8VertexIndices = struct.unpack("<3B", f.read(0x3))
					terminator = struct.unpack("<b", f.read(0x1))[0]
					mau8EdgeCosines = struct.unpack("<4B", f.read(0x4))
					PolygonSoupPolygons.append([[mu16CollisionTag_part0, mu16CollisionTag_part1], mau8VertexIndices, mau8EdgeCosines])

				PolygonSoups.append([mabVertexOffsetMultiply, PolygonSoupVertices, PolygonSoupPolygons])

	else:
		print("WARNING: failed to open PolygonSoupList %s: no such file in '%s'. Ignoring it." % (os.path.basename(polygonsouplist_path).split(".")[0], os.path.dirname(polygonsouplist_path)))

	return PolygonSoups


def read_triggerdata(triggerdata_path, resource_version): #ok
	if resource_version == "NFSHPR_PC":
		data_format = ("<Q", 0x8)
		data_format_signed = ("<q", 0x8)
	elif resource_version == "NFSHP_PC":
		data_format = ("<I", 0x4)
		data_format_signed = ("<i", 0x4)

	BoxTriggers = []
	SphereTriggers = []
	LocatorTriggers = []
	CellTriggers = []
	with open(triggerdata_path, "rb") as f:
		miVersionNumber = struct.unpack(data_format_signed[0], f.read(data_format_signed[1]))[0]
		mpaBoxTriggers = struct.unpack(data_format[0], f.read(data_format[1]))[0]
		miBoxTriggerCount = struct.unpack(data_format_signed[0], f.read(data_format_signed[1]))[0]
		mpaSphereTriggers = struct.unpack(data_format[0], f.read(data_format[1]))[0]
		miSphereTriggerCount = struct.unpack(data_format_signed[0], f.read(data_format_signed[1]))[0]
		mpaLocatorTriggers = struct.unpack(data_format[0], f.read(data_format[1]))[0]
		miLocatorTriggerCount = struct.unpack(data_format_signed[0], f.read(data_format_signed[1]))[0]
		mpaCells = struct.unpack(data_format[0], f.read(data_format[1]))[0]
		miCellCountX = struct.unpack("<i", f.read(0x4))[0]
		miCellCountZ = struct.unpack("<i", f.read(0x4))[0]
		mfMinX = struct.unpack("<f", f.read(0x4))[0]
		mfMinZ = struct.unpack("<f", f.read(0x4))[0]
		mfCellSizeX = struct.unpack("<f", f.read(0x4))[0]
		mfCellSizeZ = struct.unpack("<f", f.read(0x4))[0]

		f.seek(mpaBoxTriggers, 0)
		for i in range(0, miBoxTriggerCount):
			super_Trigger = Trigger(BytesIO(f.read(0x14)))
			mRotation = list(struct.unpack("<4f", f.read(0x10)))
			mDimension = struct.unpack("<3f", f.read(0xC))
			BoxTriggers.append([i, super_Trigger, mRotation, mDimension])

		f.seek(mpaSphereTriggers, 0)
		for i in range(0, miSphereTriggerCount):
			super_Trigger = Trigger(BytesIO(f.read(0x14)))
			mfRadius = struct.unpack("<f", f.read(0x4))[0]
			SphereTriggers.append([i, super_Trigger, mfRadius])

		f.seek(mpaLocatorTriggers, 0)
		for i in range(0, miLocatorTriggerCount):
			super_Trigger = Trigger(BytesIO(f.read(0x14)))
			mDirection = struct.unpack("<3f", f.read(0xC))
			LocatorTriggers.append([i, super_Trigger, mDirection])

		f.seek(mpaCells, 0)
		for i in range(0, miCellCountX*miCellCountZ):
			mpaTriggerIndexes = struct.unpack(data_format_signed[0], f.read(data_format_signed[1]))[0]
			miTriggerCount = struct.unpack("<h", f.read(0x2))[0]
			miPad1 = struct.unpack("<h", f.read(0x2))[0]
			if resource_version == "NFSHPR_PC":
				miPad2 = struct.unpack("<i", f.read(0x4))[0]
			#offset = f.tell()
			#f.seek(mpaTriggerIndexes, 0)
			#f.seek(offset, 0)
			CellTriggers.append([i, mpaTriggerIndexes, miTriggerCount])

	return (BoxTriggers, SphereTriggers, LocatorTriggers, CellTriggers)


def Trigger(f): #ok
	mPosition = struct.unpack("<3f", f.read(0xC))
	miOwnerId = struct.unpack("<i", f.read(0x4))[0]
	meTriggerType = struct.unpack("<b", f.read(0x1))[0]
	meTriggerShape = struct.unpack("<b", f.read(0x1))[0]
	mxFlags = struct.unpack("<b", f.read(0x1))[0]
	miPad1 = struct.unpack("<b", f.read(0x1))[0]

	meTriggerType = get_trigger_type(meTriggerType)
	meTriggerShape = get_trigger_shape(meTriggerShape)

	return (mPosition, miOwnerId, meTriggerType, meTriggerShape, mxFlags, miPad1)


def read_zonelist(zonelist_path, resource_version): #ok
	if resource_version == "NFSHPR_PC":
		data_format = ("<Q", 0x8)
		zone_length = 0x28
		neighbour_length = 0x10
		zone_length2 = 0x18
	elif resource_version == "NFSHP_PC":
		data_format = ("<I", 0x4)
		zone_length = 0x1C
		neighbour_length = 0x8
		zone_length2 = 0xC

	zones = []
	with open(zonelist_path, "rb") as f:
		mpPoints = struct.unpack(data_format[0], f.read(data_format[1]))[0]
		mpZones = struct.unpack(data_format[0], f.read(data_format[1]))[0]
		mpuZonePointStarts = struct.unpack(data_format[0], f.read(data_format[1]))[0]
		mpiZonePointCounts = struct.unpack(data_format[0], f.read(data_format[1]))[0]
		muTotalZones = struct.unpack("<I", f.read(0x4))[0]
		muTotalPoints = struct.unpack("<I", f.read(0x4))[0]
		const_0x18 = struct.unpack("<B", f.read(0x1))[0]

		points = []
		f.seek(mpPoints, 0)
		for i in range(0, muTotalPoints):
			points.append(list(struct.unpack("<2f", f.read(0x8))))
			padding = struct.unpack("<2I", f.read(0x8))

		f.seek(mpZones, 0)
		for i in range(0, muTotalZones):
			f.seek(mpZones + zone_length*i, 0)

			mpPoints = struct.unpack(data_format[0], f.read(data_format[1]))[0]
			null_0x8 = struct.unpack(data_format[0], f.read(data_format[1]))[0]

			mpNeighbours = struct.unpack(data_format[0], f.read(data_format[1]))[0]		# mpSafeNeighbours or mpUnsafeNeighbours?
			muZoneId = struct.unpack("<H", f.read(0x2))[0]
			null_0x1A = struct.unpack("<H", f.read(0x2))[0]
			muDistrictId = struct.unpack("<I", f.read(0x4))[0]

			miZoneType = struct.unpack("<H", f.read(0x2))[0]		# 1 or 0
			miNumPoints = struct.unpack("<H", f.read(0x2))[0]
			miNumSafeNeighbours = struct.unpack("<H", f.read(0x2))[0]
			miNumNeighbours = struct.unpack("<H", f.read(0x2))[0]	# miNumUnsafeNeighbours?


			#mpNeighbours
			mauNeighbourId = []
			mauNeighbourFlags = []
			f.seek(mpNeighbours, 0)
			for j in range(0, miNumNeighbours):
				f.seek(mpNeighbours + neighbour_length*j, 0)

				mpZone = struct.unpack(data_format[0], f.read(data_format[1]))[0]
				muNeighbourFlags = struct.unpack("<I", f.read(0x4))[0]	#1 or 3
				if muNeighbourFlags != 1 and muNeighbourFlags != 3:
					print("DEBUG INFO: muNeighbourFlags is different from 1 and 3.")

				f.seek(mpZone + zone_length2, 0)
				muNeighbourId = struct.unpack("<H", f.read(0x2))[0]
				mauNeighbourId.append(muNeighbourId)
				mauNeighbourFlags.append(get_neighbour_flags(muNeighbourFlags))

			#mpPoints
			f.seek(mpPoints, 0)
			zonepoints = []
			for j in range(miNumPoints):
				zonepoints.append(list(struct.unpack("<2f", f.read(0x8))))
				padding = struct.unpack("<2I", f.read(0x8))

			muArenaId = 0
			zones.append([muZoneId, [mauNeighbourId, mauNeighbourFlags, muDistrictId, miZoneType, muArenaId, miNumSafeNeighbours], zonepoints[:]])

	return zones


def read_characterspec(characterspec_path, resource_version):
	if resource_version == "NFSHPR_PC":
		data_format = ("<Q", 0x8)
	elif resource_version == "NFSHP_PC":
		data_format = ("<I", 0x4)

	instances = []
	mSkeletonId = ""
	mAnimationListId = ""
	with open(characterspec_path, "rb") as f:
		mppModels = struct.unpack(data_format[0], f.read(data_format[1]))[0]
		null_0x8 = struct.unpack(data_format[0], f.read(data_format[1]))[0]
		null_0x10 = struct.unpack(data_format[0], f.read(data_format[1]))[0]
		muNumInstances = struct.unpack("<I", f.read(0x4))[0]
		muImportCount = struct.unpack("<H", f.read(0x2))[0]
		size = struct.unpack("<H", f.read(0x2))[0]

		f.seek(mppModels, 0)
		if resource_version == "NFSHPR_PC":
			null = struct.unpack("<%dQ" % muNumInstances, f.read(0x8*muNumInstances))
		elif resource_version == "NFSHP_PC":
			null = struct.unpack("<%dI" % muNumInstances, f.read(0x4*muNumInstances))

		#Padding
		padding = calculate_padding(size, 0x10)
		f.seek(padding, 1)

		mSkeletonId = bytes_to_id(f.read(0x4))
		_ = struct.unpack("<i", f.read(0x4))[0]
		muOffset = struct.unpack("<I", f.read(0x4))[0]
		padding = struct.unpack("<i", f.read(0x4))[0]

		mAnimationListId = bytes_to_id(f.read(0x4))
		_ = struct.unpack("<i", f.read(0x4))[0]
		muOffset = struct.unpack("<I", f.read(0x4))[0]
		padding = struct.unpack("<i", f.read(0x4))[0]

		for i in range(0, muNumInstances):
			mModelId = bytes_to_id(f.read(0x4))
			_ = struct.unpack("<i", f.read(0x4))[0]
			muOffset = struct.unpack("<I", f.read(0x4))[0]
			padding = struct.unpack("<i", f.read(0x4))[0]

			instances.append([mModelId])

	return (instances, mSkeletonId, mAnimationListId)


def read_graphicsspec(graphicsspec_path, resource_version): # OK
	if resource_version == "NFSHPR_PC":
		data_format = ("<Q", 0x8)
		effect_data_length = 0x18
	elif resource_version == "NFSHP_PC":
		data_format = ("<I", 0x4)
		effect_data_length = 0xC

	instances = []
	instances_wheel = []
	instances_effects = []
	mControlMeshId = ""
	with open(graphicsspec_path, "rb") as f:
		mppModels = struct.unpack(data_format[0], f.read(data_format[1]))[0]
		null_0x8 = struct.unpack(data_format[0], f.read(data_format[1]))[0]
		null_0x10 = struct.unpack(data_format[0], f.read(data_format[1]))[0]
		mpWheelsData = struct.unpack(data_format[0], f.read(data_format[1]))[0]
		muPartsCount = struct.unpack("<H", f.read(0x2))[0]
		unknown_0x12 = struct.unpack("<B", f.read(0x1))[0]
		num_wheels = struct.unpack("<B", f.read(0x1))[0]
		num_behaviours = struct.unpack("<I", f.read(0x4))[0]
		mppBehaviour = struct.unpack(data_format[0], f.read(data_format[1]))[0]
		num_effects = struct.unpack("<I", f.read(0x4))[0]
		if resource_version == "NFSHPR_PC":
			unknown_0x34 = struct.unpack("<I", f.read(0x4))[0]		#new null
		mpEffectsId = struct.unpack(data_format[0], f.read(data_format[1]))[0]
		mpEffectsTable = struct.unpack(data_format[0], f.read(data_format[1]))[0]
		padding = f.read(0x8)
		padding = f.read(0x10)

		f.seek(mpWheelsData, 0)
		mpWheelAllocateSpace = []
		mNumWheelParts = []
		object_placements = []
		wheel_transforms = []
		is_spinnables = []
		for i in range(0, num_wheels):
			mpWheelAllocateSpace.append(struct.unpack(data_format[0], f.read(data_format[1]))[0])
			spinnable_models = struct.unpack("<I", f.read(0x4))[0]
			mNumWheelParts.append(struct.unpack("<H", f.read(0x2))[0])
			padding = f.read(0x2)
			object_placement = f.read(0x10).split(b'\x00')[0]
			object_placement = str(object_placement, 'ascii').lower()
			object_placements.append(object_placement)
			if resource_version == "NFSHPR_PC":
				null = f.read(0x10)
			elif resource_version == "NFSHP_PC":
				null = f.read(0x4)
			mWheelOffset = list(struct.unpack("<4f", f.read(0x10)))
			mWheelRotation = struct.unpack("<4f", f.read(0x10))
			mWheelScale = struct.unpack("<4f", f.read(0x10))

			wheel_transforms.append([mWheelOffset, mWheelRotation, mWheelScale])
			is_spinnables.append(bin(spinnable_models)[2:].zfill(0x8))

		first_wheel_pointer = min(mpWheelAllocateSpace)
		last_wheel_pointer = max(mpWheelAllocateSpace)
		last_wheel_index = mpWheelAllocateSpace.index(last_wheel_pointer)

		f.seek(mppBehaviour, 0)
		for i in range(0, num_behaviours):
			null_0x0 = struct.unpack(data_format[0], f.read(data_format[1]))[0]
			unknown_0x8 = struct.unpack(data_format[0], f.read(data_format[1]))[0]
			mBehaviourId = struct.unpack("<I", f.read(0x4))[0]
			unknown_0x14 = struct.unpack("<I", f.read(0x4))[0]
			unknown_0x18 = struct.unpack("<I", f.read(0x4))[0]
			if resource_version == "NFSHPR_PC":
				padding = struct.unpack("<I", f.read(0x4))[0]

		f.seek(mpEffectsId, 0)
		mEffectsId = struct.unpack("<%dI" % num_effects, f.read(0x4*num_effects))

		f.seek(mpEffectsTable, 0)
		for i in range(0, num_effects):
			f.seek(mpEffectsTable + effect_data_length*i, 0)
			effect_count = struct.unpack(data_format[0], f.read(data_format[1]))[0]
			effect_pointer = struct.unpack(data_format[0], f.read(data_format[1]))[0]
			unknown_pointer = struct.unpack(data_format[0], f.read(data_format[1]))[0]

			effectsLocation = []
			EffectData = []
			for j in range(0, effect_count):
				f.seek(effect_pointer + 0x20*j, 0)
				effectRotation = struct.unpack("<ffff", f.read(0x10))
				effectLocation = struct.unpack("<fff", f.read(0xC))
				padding = f.read(0x4)
				effectsLocation.append([effectLocation, effectRotation])

				if unknown_pointer != 0:
					f.seek(unknown_pointer + 0x4*j, 0)
					effect_data = struct.unpack("<I", f.read(0x4))[0]
					EffectData.append(effect_data)

			instances_effects.append([mEffectsId[i], i, effectsLocation[:], EffectData[:]])

		#mpResourceIds = first_wheel_pointer + sum(mNumWheelParts)*0x4
		mpResourceIds = last_wheel_pointer + mNumWheelParts[last_wheel_index]*data_format[1]
		mpResourceIds += calculate_padding(mpResourceIds, 0x10)
		if mppModels >= first_wheel_pointer:
			mpResourceIds += muPartsCount*data_format[1]
			mpResourceIds += calculate_padding(mpResourceIds, 0x10)

		f.seek(mpResourceIds, 0)
		mSkeletonId = bytes_to_id(f.read(0x4))
		_ = struct.unpack("<i", f.read(0x4))[0]
		muOffset = struct.unpack("<I", f.read(0x4))[0]
		padding = struct.unpack("<i", f.read(0x4))[0]
		if (muOffset == 0x10 and resource_version == "NFSHPR_PC") or (muOffset == 0x8 and resource_version == "NFSHP_PC"):
			mControlMeshId = mSkeletonId
			mSkeletonId = ""
			f.seek(-0x10, 1)
		elif muOffset > 0x10:
			mSkeletonId = ""
			f.seek(-0x10, 1)

		mControlMeshId = bytes_to_id(f.read(0x4))
		_ = struct.unpack("<i", f.read(0x4))[0]
		muOffset = struct.unpack("<I", f.read(0x4))[0]
		padding = struct.unpack("<i", f.read(0x4))[0]
		if muOffset > 0x10:
			mControlMeshId = ""
			f.seek(-0x10, 1)

		for i in range(0, muPartsCount):
			mModelId = bytes_to_id(f.read(0x4))
			_ = struct.unpack("<i", f.read(0x4))[0]
			muOffset = struct.unpack("<I", f.read(0x4))[0]
			padding = struct.unpack("<i", f.read(0x4))[0]

			instances.append([mModelId])

		f.seek(-0x10 * sum(mNumWheelParts), 2)
		for i in range(0, num_wheels):
			for j in range(0, mNumWheelParts[i]):
				mModelId = bytes_to_id(f.read(0x4))
				_ = struct.unpack("<i", f.read(0x4))[0]
				muOffset = struct.unpack("<I", f.read(0x4))[0]
				padding = struct.unpack("<i", f.read(0x4))[0]

				is_spinnable = bool(int(is_spinnables[i][-1-j]))
				placement = object_placements[i]

				instances_wheel.append([mModelId, [placement, is_spinnable, wheel_transforms[i]]])

	return (instances, instances_wheel, instances_effects, mSkeletonId, mControlMeshId)


def read_skeleton(skeleton_path, resource_version):
	if resource_version == "NFSHPR_PC":
		data_format = ("<Q", 0x8)
	elif resource_version == "NFSHP_PC":
		data_format = ("<I", 0x4)

	Skeleton = []
	with open(skeleton_path, "rb") as f:
		mppPointer = struct.unpack(data_format[0], f.read(data_format[1]))[0]
		mppPointer2 = struct.unpack(data_format[0], f.read(data_format[1]))[0]
		mppPointer3 = struct.unpack(data_format[0], f.read(data_format[1]))[0]
		muCount = struct.unpack(data_format[0], f.read(data_format[1]))[0]
		miNumberOfIKParts = 0

		f.seek(mppPointer, 0)
		for i in range(0, muCount):
			f.seek(mppPointer + 0x20*i, 0)
			location = struct.unpack("<fff", f.read(0xC))
			padding = f.read(0x4)
			rotation = []
			parent_sensor = struct.unpack("<i", f.read(0x4))[0]
			older_sensor = struct.unpack("<i", f.read(0x4))[0]
			child_sensor = struct.unpack("<i", f.read(0x4))[0]
			sensor_index = struct.unpack("<i", f.read(0x4))[0]

			has_ik = False

			Skeleton.append([sensor_index, location, rotation, parent_sensor, older_sensor, child_sensor, has_ik])

		f.seek(mppPointer3, 0)
		for i in range(0, muCount):
			hash = struct.unpack("<I", f.read(0x4))[0]
			Skeleton[i].append(hash)

	return Skeleton


def read_controlmesh(controlmesh_path):
	ControlMeshes = []
	with open(controlmesh_path, "rb") as f:
		unknown_0x0 = struct.unpack("<I", f.read(0x4))[0]
		size = struct.unpack("<I", f.read(0x4))[0]

		f.seek(0x10, 0)
		for i in range(0, 0x40):
			cm_coordinates_A = struct.unpack("<fff", f.read(0xC))
			w = struct.unpack("<f", f.read(0x4))[0]

			ControlMeshes.append([i, cm_coordinates_A])

		for i in range(0, 0x40):
			cm_coordinates_B = struct.unpack("<fff", f.read(0xC))
			w = struct.unpack("<f", f.read(0x4))[0]

			ControlMeshes[i].append(cm_coordinates_B)

		for i in range(0, 0x40):
			cm_limit = struct.unpack("<ffff", f.read(0x10))

			ControlMeshes[i].append(cm_limit[0])

			if len(set(cm_limit)) != 1:
				print("DEBUG: different limits found in ControlMesh file.")
				print(cm_limit)

	return ControlMeshes


def read_model(model_path, resource_version):	#OK
	if resource_version == "NFSHPR_PC":
		data_format = ("<Q", 0x8)
	elif resource_version == "NFSHP_PC":
		data_format = ("<I", 0x4)

	renderables = []
	model_properties = []
	parameters_names = []
	parameters_data = []
	samplers_names = []
	flags = []
	sampler_states = []
	textures = []
	has_tint_data = False
	with open(model_path, "rb") as f:
		mppRenderables = struct.unpack(data_format[0], f.read(data_format[1]))[0]
		mpu8StateRenderableIndices = struct.unpack(data_format[0], f.read(data_format[1]))[0]
		mpfLodDistances = struct.unpack(data_format[0], f.read(data_format[1]))[0]
		mpAdditionalData = struct.unpack(data_format[0], f.read(data_format[1]))[0]
		mu8NumRenderables = struct.unpack("<B", f.read(0x1))[0]
		mu8Flags = struct.unpack("<B", f.read(0x1))[0]
		mu8NumStates = struct.unpack("<B", f.read(0x1))[0]
		mu8VersionNumber = struct.unpack("<B", f.read(0x1))[0]
		muNumLodDistances = struct.unpack("<B", f.read(0x1))[0]
		unk_0x25 = struct.unpack("<B", f.read(0x1))[0]
		unk_0x26 = struct.unpack("<B", f.read(0x1))[0]
		unk_0x27 = struct.unpack("<B", f.read(0x1))[0]

		f.seek(mppRenderables, 0)
		if resource_version == "NFSHPR_PC":
			_ = struct.unpack("<%dQ" % mu8NumRenderables, f.read(0x8*mu8NumRenderables))
		elif resource_version == "NFSHP_PC":
			_ = struct.unpack("<%dI" % mu8NumRenderables, f.read(0x4*mu8NumRenderables))

		f.seek(mpu8StateRenderableIndices, 0)
		renderable_indices = struct.unpack("<%dB" % mu8NumStates, f.read(0x1*mu8NumStates))

		f.seek(mpfLodDistances, 0)
		lod_distances = struct.unpack("<%df" % muNumLodDistances, f.read(0x4*muNumLodDistances))

		f.seek(mppRenderables + data_format[1]*mu8NumRenderables, 0)
		padding = calculate_padding(mppRenderables + data_format[1]*mu8NumRenderables, 0x10)
		f.seek(padding, 1)

		if mpAdditionalData != 0x0:
			f.seek(mpAdditionalData, 0)
			unknown_0x0 = struct.unpack("<B", f.read(0x1))[0]
			num_parameters = struct.unpack("<B", f.read(0x1))[0]
			num_samplers = struct.unpack("<B", f.read(0x1))[0]
			unknown_0x3 = struct.unpack("<B", f.read(0x1))[0]
			if resource_version == "NFSHPR_PC":
				f.seek(0x4, 1)
			offset_0 = struct.unpack(data_format[0], f.read(data_format[1]))[0]
			offset_1 = struct.unpack(data_format[0], f.read(data_format[1]))[0]
			offset_2 = struct.unpack(data_format[0], f.read(data_format[1]))[0]
			offset_3 = struct.unpack(data_format[0], f.read(data_format[1]))[0]
			offset_4 = struct.unpack(data_format[0], f.read(data_format[1]))[0]
			mpaSamplersStates = struct.unpack(data_format[0], f.read(data_format[1]))[0]
			mpaTextures = struct.unpack(data_format[0], f.read(data_format[1]))[0]

			if num_parameters == 0 and num_samplers == 0:
				print("Debug: InstanceList entry has num_parameters == 0 and num_samplers == 0")

			if num_parameters != 0:
				has_tint_data = True
				f.seek(offset_0, 0)
				offset_0_1 = struct.unpack("<%dQ" % num_parameters, f.read(0x8*num_parameters))

				for offset in offset_0_1:
					f.seek(offset, 0)
					parameter_name = f.read(0x20).split(b'\x00')[0]
					parameter_name = str(parameter_name, 'ascii')
					parameters_names.append(parameter_name)

				f.seek(offset_1, 0)
				flags = struct.unpack("<%db" % num_parameters, f.read(0x1*num_parameters))

				f.seek(offset_2, 0)
				for j in range(0, num_parameters):
					parameters_data.append(struct.unpack("<4f", f.read(0x10)))

			if num_samplers != 0:
				has_tint_data = True
				f.seek(offset_3, 0)
				if resource_version == "NFSHPR_PC":
					offset_3_1 = struct.unpack("<%dQ" % num_samplers, f.read(0x8*num_samplers))
				elif resource_version == "NFSHP_PC":
					offset_3_1 = struct.unpack("<%dI" % num_samplers, f.read(0x4*num_samplers))

				for offset in offset_3_1:
					f.seek(offset, 0)
					sampler_name = f.read(0x20).split(b'\x00')[0]
					sampler_name = str(sampler_name, 'ascii')
					samplers_names.append(sampler_name)

				f.seek(offset_4, 0)
				flags = struct.unpack("<%db" % num_samplers, f.read(0x1*num_samplers))

				f.seek(mpaSamplersStates, 0)
				if resource_version == "NFSHPR_PC":
					_ = struct.unpack("<%dQ" % num_samplers, f.read(0x8*num_samplers))
				elif resource_version == "NFSHP_PC":
					_ = struct.unpack("<%dI" % num_samplers, f.read(0x4*num_samplers))

				f.seek(mpaTextures, 0)
				if resource_version == "NFSHPR_PC":
					_ = struct.unpack("<%dQ" % num_samplers, f.read(0x8*num_samplers))
				elif resource_version == "NFSHP_PC":
					_ = struct.unpack("<%dI" % num_samplers, f.read(0x4*num_samplers))

				for j in range(0, num_samplers):
					f.seek(-0x8, 2)
					pointer = struct.unpack("<I", f.read(0x4))[0]
					while pointer != (mpaSamplersStates + data_format[1]*j):
						f.seek(-0x14, 1)
						pointer = struct.unpack("<I", f.read(0x4))[0]
					f.seek(-0xC, 1)
					mSamplerStateId = bytes_to_id(f.read(0x4))
					f.seek(-0x4, 1)
					f.seek(0x10*num_samplers, 1)
					mTextureId = bytes_to_id(f.read(0x4))

					sampler_states.append(mSamplerStateId)
					textures.append(mTextureId)

			f.seek(-0x10*num_samplers*2 - 0x10*mu8NumRenderables, 2)

		for i in range(0, mu8NumRenderables):
			mResourceId = bytes_to_id(f.read(0x4))
			_ = struct.unpack("<i", f.read(0x4))[0]
			muOffset = struct.unpack("<I", f.read(0x4))[0]
			padding = struct.unpack("<i", f.read(0x4))[0]

			#renderables.append([mResourceId, [renderable_indices[i], lod_distances[i]]])
			renderables.append([mResourceId, [i, 0]])

		model_properties = [mu8Flags, renderable_indices, lod_distances, has_tint_data, parameters_names, parameters_data, samplers_names, sampler_states, textures, unk_0x25]

	return (model_properties, renderables)


def read_renderable(renderable_path, resource_version): # OK
	if resource_version == "NFSHPR_PC":
		data_format = ("<Q", 0x8)
	elif resource_version == "NFSHP_PC":
		data_format = ("<I", 0x4)

	meshes = []
	renderable_properties = []
	with open(renderable_path, "rb") as f:
		object_center = struct.unpack("<fff", f.read(0xC))
		object_radius = struct.unpack("<f", f.read(0x4))[0]
		mu16VersionNumber = struct.unpack("<H", f.read(0x2))[0]
		num_meshes = struct.unpack("<H", f.read(0x2))[0]
		if resource_version == "NFSHPR_PC":
			padding = struct.unpack("<I", f.read(0x4))[0]
		meshes_table_pointer = struct.unpack(data_format[0], f.read(data_format[1]))[0]
		flags0 = struct.unpack("<b", f.read(0x1))[0]
		flags1 = struct.unpack("<b", f.read(0x1))[0]
		padding = f.read(0x2)
		#padding = f.read(0xC)

		f.seek(meshes_table_pointer, 0)
		if resource_version == "NFSHPR_PC":
			meshes_data_pointer = struct.unpack("<%dQ" % num_meshes, f.read(0x8*num_meshes))
		elif resource_version == "NFSHP_PC":
			meshes_data_pointer = struct.unpack("<%dI" % num_meshes, f.read(0x4*num_meshes))

		renderable_properties = [object_center, object_radius, flags0, flags1]

		# read meshes data
		for i in range(0, num_meshes):
			f.seek(meshes_data_pointer[i], 0)
			submesh_center0, factor0, submesh_center1, submesh_center2 = struct.unpack("<hHhh", f.read(0x8))
			submesh_scale = list(struct.unpack("<BBB", f.read(0x3)))
			factor1 = struct.unpack("<B", f.read(0x1))[0]
			submesh_quaternion = list(struct.unpack("<bbbb", f.read(0x4)))
			primitive_topology = struct.unpack("<i", f.read(0x4))[0]		# always 0x5, verify
			null_0x14 = struct.unpack("<i", f.read(0x4))[0]					# base_vertex_index on HP
			null_0x18 = struct.unpack("<i", f.read(0x4))[0]					# start_index on HP
			indices_buffer_count = struct.unpack("<i", f.read(0x4))[0]		# number_of_indices, similar to indices_buffer_count on HP
			null_0x20 = struct.unpack("<i", f.read(0x4))[0]					# minimum_index on HP
			unk_0x24 = struct.unpack("<i", f.read(0x4))[0]					# number_of_primitives on HP, null on HPR
			if resource_version == "NFSHP_PC":
				unk_0x28 = struct.unpack("<i", f.read(0x4))[0]				# mpMaterialAssembly on HP
			mu8Flags = struct.unpack("<B", f.read(0x1))[0]
			mu8NumVertexBuffers = struct.unpack("<B", f.read(0x1))[0]
			mu8InstanceCount = struct.unpack("<B", f.read(0x1))[0]
			mu8NumVertexDescriptors = struct.unpack("<B", f.read(0x1))[0]
			if resource_version == "NFSHPR_PC":
				null_0x2C = struct.unpack("<i", f.read(0x4))[0]

			pointers_1 = struct.unpack(data_format[0], f.read(data_format[1]))[0]
			pointers_2 = struct.unpack(data_format[0], f.read(data_format[1]))[0]

			if resource_version == "NFSHPR_PC":
				f.seek(pointers_1, 0)
				buffer_interface = struct.unpack("<q", f.read(0x8))[0]
				buffer_usage = struct.unpack("<i", f.read(0x4))[0]
				buffer_type = struct.unpack("<i", f.read(0x4))[0]
				if buffer_type == 0x3:
					indices_buffer_offset = struct.unpack("<q", f.read(0x8))[0]
					indices_buffer_size = struct.unpack("<I", f.read(0x4))[0]	#includes padding
					indices_size = struct.unpack("<I", f.read(0x4))[0]	#2 or 4 bytes
				elif buffer_type == 0x2:
					vertices_buffer_offset = struct.unpack("<q", f.read(0x8))[0]
					vertices_buffer_size = struct.unpack("<I", f.read(0x4))[0]	#includes padding
					unk = struct.unpack("<i", f.read(0x4))[0]
					unk = struct.unpack("<i", f.read(0x4))[0]

				f.seek(pointers_2, 0)
				buffer_interface = struct.unpack("<q", f.read(0x8))[0]
				buffer_usage = struct.unpack("<i", f.read(0x4))[0]
				buffer_type = struct.unpack("<i", f.read(0x4))[0]
				if buffer_type == 0x3:
					indices_buffer_offset = struct.unpack("<q", f.read(0x8))[0]
					indices_buffer_size = struct.unpack("<I", f.read(0x4))[0]	#includes padding
					indices_size = struct.unpack("<I", f.read(0x4))[0]	#2 or 4 bytes
				elif buffer_type == 0x2:
					vertices_buffer_offset = struct.unpack("<q", f.read(0x8))[0]
					vertices_buffer_size = struct.unpack("<I", f.read(0x4))[0]	#includes padding
					unk = struct.unpack("<i", f.read(0x4))[0]
					unk = struct.unpack("<i", f.read(0x4))[0]

				padding = f.read(0xC)

			elif resource_version == "NFSHP_PC":
				f.seek(pointers_1, 0)
				indices_buffer_count = struct.unpack(data_format[0], f.read(data_format[1]))[0]
				indices_buffer_offset = struct.unpack(data_format[0], f.read(data_format[1]))[0]
				null_0x58 = struct.unpack(data_format[0], f.read(data_format[1]))[0]
				indices_buffer_flags = struct.unpack(data_format[0], f.read(data_format[1]))[0]
				indices_size = 0x2

				vertices_buffer_offset = struct.unpack(data_format[0], f.read(data_format[1]))[0]
				null_0x64 = struct.unpack(data_format[0], f.read(data_format[1]))[0]
				vertices_buffer_size = struct.unpack(data_format[0], f.read(data_format[1]))[0]
				padding = struct.unpack(data_format[0], f.read(data_format[1]))[0]

			mesh_properties = [indices_buffer_offset, indices_buffer_count, indices_size, vertices_buffer_offset, vertices_buffer_size]
			meshes.append([i, mesh_properties])


		# This part could be incorrect on models exported by other tools
		num_resources = num_meshes
		resource_table_size = num_resources*0x10
		f.seek(-resource_table_size, 2)

		if resource_version == "NFSHPR_PC":
			muMaterialOffset_first = meshes_data_pointer[0] + 0x20
		elif resource_version == "NFSHP_PC":
			muMaterialOffset_first = meshes_data_pointer[0] + 0x28

		f.seek(-0x8, 2)
		check = struct.unpack("<H", f.read(0x2))[0]
		count = 1
		while check != muMaterialOffset_first:
			f.seek(-0x12, 1)
			check = struct.unpack("<H", f.read(0x2))[0]
			count = count + 1
		num_resources = count
		muImportOffset = os.path.getsize(renderable_path) - num_resources*0x10
		f.seek(muImportOffset, 0)


		for i in range(0, num_meshes):
			mMaterialId = bytes_to_id(f.read(0x4))
			_ = struct.unpack("<B", f.read(0x1))[0]
			_ = struct.unpack("<B", f.read(0x1))[0]
			_ = struct.unpack("<B", f.read(0x1))[0]
			_ = struct.unpack("<B", f.read(0x1))[0]
			muOffset = struct.unpack("<I", f.read(0x4))[0]
			padding = struct.unpack("<i", f.read(0x4))[0]

			meshes[i].append(mMaterialId)

	return (renderable_properties, meshes)


def read_vertex_descriptor(vertex_descriptor_path, resource_version): # OK
	vertex_properties = []
	with open(vertex_descriptor_path, "rb") as f:
		if resource_version == "NFSHPR_PC":
			unk1 = struct.unpack("<I", f.read(0x4))[0]
			attibutes_flags = struct.unpack("<I", f.read(0x4))[0]
			_ = struct.unpack("<I", f.read(0x4))[0] #null
			num_vertex_attibutes = struct.unpack("<B", f.read(0x1))[0]
			num_streams = struct.unpack("<B", f.read(0x1))[0]
			elements_hash = struct.unpack("<H", f.read(0x2))[0]

			semantic_properties = []
			for i in range(0, num_vertex_attibutes):
				semantic_type = struct.unpack("<B", f.read(0x1))[0]
				semantic_index = struct.unpack("<B", f.read(0x1))[0]
				input_slot = struct.unpack("<B", f.read(0x1))[0]
				element_class = struct.unpack("<B", f.read(0x1))[0]
				data_type = struct.unpack("<i", f.read(0x4))[0]
				data_offset = struct.unpack("<i", f.read(0x4))[0]
				step_rate = struct.unpack("<i", f.read(0x4))[0] #null
				vertex_size = struct.unpack("<i", f.read(0x4))[0]

				semantic_type = get_vertex_semantic(semantic_type)
				data_type = get_vertex_data_type(data_type)

				semantic_properties.append([semantic_type, data_type, data_offset])

		elif resource_version == "NFSHP_PC":
			unk1 = struct.unpack("<i", f.read(0x4))[0]
			_ = struct.unpack("<i", f.read(0x4))[0] #null
			attibutes_flags = struct.unpack("<i", f.read(0x4))[0]
			num_vertex_attibutes = struct.unpack("<B", f.read(0x1))[0]
			num_streams = struct.unpack("<B", f.read(0x1))[0]
			address_hash = f.read(0x2)

			semantic_properties = []
			for i in range(0, num_vertex_attibutes):
				stream_index = struct.unpack("<B", f.read(0x1))[0]
				vertex_size = struct.unpack("<B", f.read(0x1))[0]
				data_offset = struct.unpack("<H", f.read(0x2))[0]
				data_type = struct.unpack("<B", f.read(0x1))[0]
				padding = f.read(0x3)
				tessellation_method = struct.unpack("<B", f.read(0x1))[0]
				data_usage = struct.unpack("<B", f.read(0x1))[0]
				usage_index = struct.unpack("<B", f.read(0x1))[0]
				indexed_usage = struct.unpack("<B", f.read(0x1))[0]
				element_class = struct.unpack("<I", f.read(0x4))[0]

				semantic_type = get_vertex_semantic_d3d9(indexed_usage)
				data_type = get_vertex_data_type_d3d9(data_type)

				semantic_properties.append([semantic_type, data_type, data_offset])

		vertex_properties = [vertex_size, [semantic_properties]]

	return vertex_properties


def read_material(material_path, shared_shader_dir, resource_version): # OK
	if resource_version == "NFSHPR_PC":
		data_format = ("<Q", 0x8)
	elif resource_version == "NFSHP_PC":
		data_format = ("<I", 0x4)

	material_properties = []
	mShaderId = ""
	textures = []
	sampler_states = []
	with open(material_path, "rb") as f:
		# Reading header
		Id = struct.unpack("<I", f.read(0x4))[0]	# ?
		null1 = struct.unpack("<B", f.read(0x1))[0]
		const0x5 = struct.unpack("<B", f.read(0x1))[0]
		resources_pointer = struct.unpack("<H", f.read(0x2))[0]
		null = struct.unpack(data_format[0], f.read(data_format[1]))[0]
		parameters_indices_pointer = struct.unpack(data_format[0], f.read(data_format[1]))[0]
		parameters_ones_pointer = struct.unpack(data_format[0], f.read(data_format[1]))[0]
		parameters_nameshash_pointer = struct.unpack(data_format[0], f.read(data_format[1]))[0]
		parameters_data_pointer = struct.unpack(data_format[0], f.read(data_format[1]))[0]
		num_parameters = struct.unpack("<B", f.read(0x1))[0]
		num_parameters_withdata = struct.unpack("<B", f.read(0x1))[0]
		null2 = struct.unpack("<B", f.read(0x1))[0]
		null3 = struct.unpack("<B", f.read(0x1))[0]
		if resource_version == "NFSHPR_PC":
			null_ = struct.unpack("<I", f.read(0x4))[0]
		miNumSamplers = struct.unpack("<B", f.read(0x1))[0]
		null4 = struct.unpack("<B", f.read(0x1))[0]
		null5 = struct.unpack("<B", f.read(0x1))[0]
		null6 = struct.unpack("<B", f.read(0x1))[0]
		if resource_version == "NFSHPR_PC":
			null_ = struct.unpack("<I", f.read(0x4))[0]
		mpaMaterialConstants = struct.unpack(data_format[0], f.read(data_format[1]))[0]
		mpaSamplersChannel = struct.unpack(data_format[0], f.read(data_format[1]))[0]
		mpaSamplers = struct.unpack(data_format[0], f.read(data_format[1]))[0]

		# Reading data
		if num_parameters > 0:
			f.seek(parameters_indices_pointer, 0)
			parameters_Indices = list(struct.unpack("<%db" % num_parameters, f.read(0x1*num_parameters)))

			f.seek(parameters_ones_pointer, 0)
			parameters_Ones = list(struct.unpack("<%db" % num_parameters, f.read(0x1*num_parameters)))

			f.seek(parameters_nameshash_pointer, 0)
			parameters_NamesHash = list(struct.unpack("<%dI" % num_parameters, f.read(0x4*num_parameters)))

			f.seek(parameters_data_pointer, 0)
			parameters_Data = []
			# for i in range(0, num_parameters):
				# if parameters_Indices[i] == -1:
					# parameters_Data.append(None)
				# else:
					# parameters_Data.append(struct.unpack("<4f", f.read(0x10)))

			for i in range(0, num_parameters):
				if parameters_Indices[i] == -1:
					parameters_Data.append(None)
				else:
					f.seek(parameters_data_pointer + 0x10*parameters_Indices[i], 0)
					parameters_Data.append(struct.unpack("<4f", f.read(0x10)))
					#parameters_names.append(shader_parameters_Names[i])

		else:
			parameters_Indices = []
			parameters_Ones = []
			parameters_NamesHash = []
			parameters_Data = []
			parameters_Names = []

		f.seek(resources_pointer, 0)
		mShaderId = bytes_to_id(f.read(0x4))
		_ = struct.unpack("<i", f.read(0x4))[0]
		muOffset = struct.unpack("<I", f.read(0x4))[0]
		padding = struct.unpack("<i", f.read(0x4))[0]

		for i in range(0, miNumSamplers):
			mTextureId = bytes_to_id(f.read(0x4))
			_ = struct.unpack("<i", f.read(0x4))[0]
			muOffset = struct.unpack("<I", f.read(0x4))[0]
			padding = struct.unpack("<i", f.read(0x4))[0]

			textures.append([mTextureId])

		for i in range(0, miNumSamplers):
			mSamplerStateId = bytes_to_id(f.read(0x4))
			_ = struct.unpack("<i", f.read(0x4))[0]
			muOffset = struct.unpack("<I", f.read(0x4))[0]
			padding = struct.unpack("<i", f.read(0x4))[0]

			sampler_states.append([mSamplerStateId])

		#if num_parameters > 0:
		shader_path = os.path.join(shared_shader_dir, mShaderId + "_83.dat")
		shader_type, _, _, _, shader_parameters, _, texture_samplers, vertex_properties = read_shader(shader_path, resource_version)
		shader_parameters_Indices = shader_parameters[0]
		shader_parameters_Names = shader_parameters[4]
		shader_parameters_NamesHash = shader_parameters[2]

		semantic_types = []
		for semantic_property in vertex_properties[1][0]:
			semantic_types.append(semantic_property[0])

		if miNumSamplers != len(texture_samplers):
			print("WARNING: number of texture samplers (%d) defined on material %s is different from the %d specified by the shader %s. Setting as 'Undefined'. The other sampler names might be incorredly setted." % (miNumSamplers, os.path.basename(material_path).split(".")[0], len(texture_samplers), mShaderId))
			i = 0
			while miNumSamplers != len(texture_samplers):
				texture_samplers.append("Undefined_%d" % i)
				i += 1

		parameters_Names = []
		for i in range(0, len(parameters_NamesHash)):
			parameters_Names.append(shader_parameters_Names[i])

		for i in range(0, miNumSamplers):
			textures[i].append(texture_samplers[i])

		material_properties.append([parameters_Data, parameters_Names])

	return (material_properties, mShaderId, shader_type, sampler_states, textures, semantic_types)


def read_shader(shader_path, resource_version): # OK
	if resource_version == "NFSHPR_PC":
		data_format = ("<Q", 0x8)
	elif resource_version == "NFSHP_PC":
		data_format = ("<I", 0x4)

	ShaderType = ""
	raster_types = []
	texture_samplers = []
	with open(shader_path, "rb") as f:
		file_size = os.path.getsize(shader_path)

		# Shader description
		pointer_0 = struct.unpack(data_format[0], f.read(data_format[1]))[0]
		pointer_1 = struct.unpack(data_format[0], f.read(data_format[1]))[0]
		shader_description_offset = struct.unpack(data_format[0], f.read(data_format[1]))[0]
		f.seek(0x4, 1)
		end_sampler_types_offset = struct.unpack("<H", f.read(0x2))[0]
		resources_pointer = struct.unpack("<H", f.read(0x2))[0]
		shader_parameters_pointers = f.tell()
		f.seek(shader_description_offset, 0)
		shader_description = f.read(resources_pointer-shader_description_offset).split(b'\x00')[0]
		shader_description = str(shader_description, 'ascii')

		# Shader parameters
		f.seek(shader_parameters_pointers, 0)
		shader_parameters_indices_pointer = struct.unpack(data_format[0], f.read(data_format[1]))[0]
		shader_parameters_ones_pointer = struct.unpack(data_format[0], f.read(data_format[1]))[0]
		shader_parameters_nameshash_pointer = struct.unpack(data_format[0], f.read(data_format[1]))[0]
		shader_parameters_data_pointer = struct.unpack(data_format[0], f.read(data_format[1]))[0]
		num_shader_parameters = struct.unpack("<B", f.read(0x1))[0]
		num_shader_parameters_withdata = struct.unpack("<B", f.read(0x1))[0]
		f.seek(0x2, 1)
		if resource_version == "NFSHPR_PC":
			f.seek(0x4, 1)
		shader_parameters_names_pointer = struct.unpack(data_format[0], f.read(data_format[1]))[0]
		shader_parameters_end_pointer = struct.unpack(data_format[0], f.read(data_format[1]))[0]
		if shader_parameters_end_pointer == 0:
			shader_parameters_end_pointer = end_sampler_types_offset

		f.seek(shader_parameters_indices_pointer, 0)
		shader_parameters_Indices = list(struct.unpack("<%db" % num_shader_parameters, f.read(0x1*num_shader_parameters)))

		f.seek(shader_parameters_ones_pointer, 0)
		shader_parameters_Ones = list(struct.unpack("<%db" % num_shader_parameters, f.read(0x1*num_shader_parameters)))

		f.seek(shader_parameters_nameshash_pointer, 0)
		shader_parameters_NamesHash = list(struct.unpack("<%dI" % num_shader_parameters, f.read(0x4*num_shader_parameters)))

		f.seek(shader_parameters_data_pointer, 0)
		shader_parameters_Data = []
		# for i in range(0, num_shader_parameters):
			# if shader_parameters_Indices[i] == -1:
				# shader_parameters_Data.append(None)
			# else:
				# shader_parameters_Data.append(struct.unpack("<4f", f.read(0x10)))

		for i in range(0, num_shader_parameters):
			if shader_parameters_Indices[i] == -1:
				shader_parameters_Data.append(None)
			else:
				f.seek(shader_parameters_data_pointer + 0x10*shader_parameters_Indices[i], 0)
				shader_parameters_Data.append(struct.unpack("<4f", f.read(0x10)))
				#parameters_names.append(shader_parameters_Names[i])

		shader_parameters_Names = []
		#shader_parameters_Names = [""]*num_shader_parameters
		for i in range(0, num_shader_parameters):
			f.seek(shader_parameters_names_pointer + i*data_format[1], 0)
			pointer = struct.unpack(data_format[0], f.read(data_format[1]))[0]
			f.seek(pointer, 0)
			parameter_name = f.read(shader_parameters_end_pointer-pointer).split(b'\x00')[0]
			parameter_name = str(parameter_name, 'ascii')
			shader_parameters_Names.append(parameter_name)
			#shader_parameters_Names[shader_parameters_Indices[i]] = parameter_name

		shader_parameters = [shader_parameters_Indices, shader_parameters_Ones, shader_parameters_NamesHash, shader_parameters_Data, shader_parameters_Names]

		# Samplers and material constants
		if resource_version == "NFSHPR_PC":
			f.seek(0xB0, 0)
		elif resource_version == "NFSHP_PC":
			f.seek(0x5C, 0)
		miNumSamplers = struct.unpack("<B", f.read(0x1))[0]
		f.seek(0x3, 1)
		if resource_version == "NFSHPR_PC":
			f.seek(0x4, 1)
		mpaMaterialConstants = struct.unpack(data_format[0], f.read(data_format[1]))[0]
		mpaSamplersChannel = struct.unpack(data_format[0], f.read(data_format[1]))[0]
		mpaSamplers = struct.unpack(data_format[0], f.read(data_format[1]))[0]
		if resource_version == "NFSHPR_PC":
			f.seek(0xF8, 0)
		elif resource_version == "NFSHP_PC":
			f.seek(0x80, 0)
		end_raster_types_offset = struct.unpack("<i", f.read(0x4))[0]
		if end_raster_types_offset == 0:
			end_raster_types_offset = end_sampler_types_offset

		f.seek(mpaMaterialConstants, 0)
		material_constants = struct.unpack("<%dH" % miNumSamplers, f.read(0x2*miNumSamplers))

		f.seek(mpaSamplersChannel, 0)
		miChannel = struct.unpack("<%dB" % miNumSamplers, f.read(0x1*miNumSamplers))

		f.seek(mpaSamplers, 0)
		if resource_version == "NFSHPR_PC":
			raster_type_offsets = list(struct.unpack("<%dQ" % miNumSamplers, f.read(0x8*miNumSamplers)))
		elif resource_version == "NFSHP_PC":
			raster_type_offsets = list(struct.unpack("<%dI" % miNumSamplers, f.read(0x4*miNumSamplers)))
		raster_type_offsets.append(end_raster_types_offset)

		for i in range(0, miNumSamplers):
			f.seek(raster_type_offsets[i], 0)
			if raster_type_offsets[i] > raster_type_offsets[i+1]:
				raster_type = f.read(end_raster_types_offset-raster_type_offsets[i]).split(b'\x00')[0]
			else:
				raster_type = f.read(raster_type_offsets[i+1]-raster_type_offsets[i]).split(b'\x00')[0]
			raster_type = str(raster_type, 'ascii')
			raster_types.append([miChannel[i], raster_type])
			texture_samplers.append(raster_type)

		raster_types.sort(key=lambda x:x[0])

		raster_types_dict = {}
		for raster_type_data in raster_types:
			raster_types_dict[raster_type_data[0]] = raster_type_data[1]

		if shader_description == "DEBUG_TRIGGER_Illuminance_Greyscale_Singlesided":
			texture_samplers.insert(-1, "IlluminanceTextureSampler")

		# VertexDescriptor
		f.seek(resources_pointer, 0)
		mVertexDescriptorId = bytes_to_id(f.read(0x4))

		if resource_version == "NFSHPR_PC":
			shared_dir = os.path.join(NFSHPLibraryGet(), "NFSHPR_Library_PC")
		elif resource_version == "NFSHP_PC":
			shared_dir = os.path.join(NFSHPLibraryGet(), "NFSHP_Library_PC")
		shared_vertex_descriptor_dir = os.path.join(os.path.join(shared_dir, "SHADERS"), "VertexDescriptor")
		vertex_descriptor_path = os.path.join(shared_vertex_descriptor_dir, mVertexDescriptorId + ".dat")
		vertex_properties = read_vertex_descriptor(vertex_descriptor_path, resource_version)

	return (shader_description, mVertexDescriptorId, miNumSamplers, raster_types_dict, shader_parameters, material_constants, texture_samplers, vertex_properties)


def read_texture(texture_path, resource_version): # OK
	texture_properties = []
	if os.path.splitext(texture_path)[1] == ".dds":
		with open(texture_path, "rb") as f:
			DDS_MAGIC = struct.unpack("<I", f.read(0x4))[0]
			header_size = struct.unpack("<I", f.read(0x4))[0]
			flags = struct.unpack("<I", f.read(0x4))[0]
			height = struct.unpack("<I", f.read(0x4))[0]
			width = struct.unpack("<I", f.read(0x4))[0]
			pitchOrLinearSize = struct.unpack("<I", f.read(0x4))[0]
			depth = struct.unpack("<I", f.read(0x4))[0]
			mipMapCount = struct.unpack("<I", f.read(0x4))[0]
			reserved1 = struct.unpack("<11I", f.read(0x4*11))

			# DDS_PIXELFORMAT
			dwSize = struct.unpack("<I", f.read(0x4))[0]
			dwFlags = struct.unpack("<I", f.read(0x4))[0]
			dwFourCC = f.read(0x4).decode()
			dwRGBBitCount = struct.unpack("<I", f.read(0x4))[0]
			dwRBitMask = struct.unpack("<I", f.read(0x4))[0]
			dwGBitMask = struct.unpack("<I", f.read(0x4))[0]
			dwBBitMask = struct.unpack("<I", f.read(0x4))[0]
			dwABitMask = struct.unpack("<I", f.read(0x4))[0]

			caps = struct.unpack("<I", f.read(0x4))[0]
			caps2 = struct.unpack("<I", f.read(0x4))[0]
			caps3 = struct.unpack("<I", f.read(0x4))[0]
			caps4 = struct.unpack("<I", f.read(0x4))[0]
			reserved2 = struct.unpack("<I", f.read(0x4))[0]

			if depth == 0:
				depth = 1

			#format = get_raster_format(dwFourCC)
			texture_properties = [dwFourCC, width, height, depth, 1, 1, mipMapCount, 0x30]

		return texture_properties

	with open(texture_path, "rb") as f:
		if resource_version == "NFSHPR_PC":
			texture_interface = struct.unpack("<q", f.read(0x8))[0]	#null, maybe a pointer D3D11_TEXTURE1D_DESC* (Pointer to a resource description)
			usage = struct.unpack("<i", f.read(0x4))[0]
			dimension = struct.unpack("<i", f.read(0x4))[0]
			pixel_data = struct.unpack("<q", f.read(0x8))[0]	#null
			_ = struct.unpack("<q", f.read(0x8))[0]	#null
			_ = struct.unpack("<q", f.read(0x8))[0]	#null
			_ = struct.unpack("<i", f.read(0x4))[0]
			format = struct.unpack("<i", f.read(0x4))[0]
			flags = struct.unpack("<I", f.read(0x4))[0]		#0x30, normal = 0x20
			width, height, depth = struct.unpack("<HHH", f.read(0x6))
			array_size = struct.unpack("<H", f.read(0x2))[0]
			main_mipmap, mipmap = struct.unpack("<BB", f.read(0x2))
			_ = struct.unpack("<H", f.read(0x2))[0]

			# remap, pitch, storeFlags

			format = get_fourcc(format)

			if dimension == 6:	 # 1D
				dimension = 1
			elif dimension == 7: # 2D
				dimension = 2
			elif dimension == 8: # 3D
				dimension = 3
			elif dimension == 9: # Cube texture
				dimension = 4

		elif resource_version == "NFSHP_PC":
			_ = struct.unpack("<i", f.read(0x4))[0]
			_ = struct.unpack("<i", f.read(0x4))[0]
			memory_class = struct.unpack("<H", f.read(0x2))[0]
			_ = struct.unpack("<B", f.read(0x1))[0]
			_ = struct.unpack("<B", f.read(0x1))[0]
			format = f.read(0x4)
			if format != b'\x44\x58\x54\x31' and format != b'\x44\x58\x54\x35' and format != b'\x44\x58\x54\x33':
				format = get_fourcc(struct.unpack("<i", format)[0])
			else:
				format = str(format, 'ascii')
			width, height, depth = struct.unpack("<HHB", f.read(0x5))
			mipmap = struct.unpack("<B", f.read(0x1))[0]
			dimension = struct.unpack("<B", f.read(0x1))[0]
			flags = struct.unpack("<B", f.read(0x1))[0]
			if dimension == 0x0: #2D texture
				dimension = 1
			elif dimension == 0x1: #1D (cube) texture
				dimension = 0
			elif dimension == 0x2: #3D (volume) texture
				dimension = 2
			elif dimension == 0x3: #2D texture
				dimension = 1

			main_mipmap = 0

		texture_properties = [format, width, height, depth, dimension,
							  main_mipmap, mipmap, flags]

	return texture_properties


def read_genesysinstance_driver(genesyinstance_dir, genesysinstance_path, resource_version):
	instance_character = []
	with open(genesysinstance_path, "rb") as f:
		if resource_version == "NFSHPR_PC":
			f.seek(0x30, 0)
		elif resource_version == "NFSHP_PC":
			f.seek(0x20, 0)
		characterOffset = list(struct.unpack("<fff", f.read(0xC)))

		mCharacterSpecID = ""

		instance_character = [mCharacterSpecID, characterOffset]

	return instance_character


def read_genesysinstance_wheels(genesyinstance_dir, genesysinstance_path, instances_wheel, resource_version):
	#instances_wheel = [mModelId, [placement, is_spinnable, wheel_transforms[i]]]
	#wheel_transforms = [mWheelOffset, mWheelRotation, mWheelScale]

	if resource_version == "NFSHPR_PC":
		data_format = ("<Q", 0x8)
	elif resource_version == "NFSHP_PC":
		data_format = ("<I", 0x4)

	offsetsY = []
	with open(genesysinstance_path, "rb") as f:
		# f.seek(0x158, 0)
		# wheel_table_pointer = struct.unpack("<Q", f.read(0x8))[0]
		# wheel_count = struct.unpack("<I", f.read(0x4))[0]

		# for i in range(0, wheel_count):
			# f.seek(wheel_table_pointer + 0x8*i, 0)
			# wheel_data_pointer = struct.unpack("<Q", f.read(0x8))[0]

			# f.seek(wheel_data_pointer + 0x10, 0)
			# wheel_coordinates_pointer = struct.unpack("<Q", f.read(0x8))[0]

			# f.seek(wheel_coordinates_pointer, 0)
			# instance[1][2][0] = struct.unpack("<fff", f.read(0xC))

		if resource_version == "NFSHPR_PC":
			f.seek(0x128, 0)
		elif resource_version == "NFSHP_PC":
			f.seek(0x108, 0)

		table_pointer = struct.unpack(data_format[0], f.read(data_format[1]))[0]
		count = struct.unpack("<I", f.read(0x4))[0]

		f.seek(table_pointer, 0)
		if resource_version == "NFSHPR_PC":
			data_pointers = list(struct.unpack("<%dQ" % count, f.read(0x8*count)))
		elif resource_version == "NFSHP_PC":
			data_pointers = list(struct.unpack("<%dI" % count, f.read(0x4*count)))
		placements = ["unknown", "rearright", "rearleft", "frontright", "frontleft"]

		for i in range(0, count):
			f.seek(data_pointers[i], 0)
			if resource_version == "NFSHPR_PC":
				f.seek(0x10, 1)
			elif resource_version == "NFSHP_PC":
				f.seek(0x8, 1)
			wheel_data_pointer = struct.unpack(data_format[0], f.read(data_format[1]))[0]

			f.seek(wheel_data_pointer, 0)

			mTransform = [[*struct.unpack("<4f", f.read(0x10))],[*struct.unpack("<4f", f.read(0x10))],[*struct.unpack("<4f", f.read(0x10))],[*struct.unpack("<4f", f.read(0x10))]]
			mTransform = Matrix(mTransform)
			mTransform = mTransform.transposed()

			mWheelOffset, mWheelRotation, mWheelScale = mTransform.decompose()

			for instance in instances_wheel:
				if instance[1][0] == placements[i].lower():
					instance[1][2] = [mWheelOffset, mWheelRotation, mWheelScale]

	return instances_wheel


def create_renderable(renderable, materials, shaders, resource_type):
	mRenderableId = renderable[0]
	meshes_info = renderable[1][0]
	renderable_properties = renderable[1][1]
	is_shared_asset = renderable[-2]
	renderable_path = renderable[-1]

	num_meshes = len(meshes_info)
	renderable_body_path = os.path.splitext(renderable_path)[0] + "_model" + os.path.splitext(renderable_path)[1]

	with open(renderable_body_path, "rb") as f:
		indices_buffer = [[] for _ in range(num_meshes)]
		vertices_buffer = [[] for _ in range(num_meshes)]
		sensors_list = []
		bones_list = []

		for mesh_info in meshes_info:
			mesh_index = mesh_info[0]
			mesh_properties = mesh_info[1]
			mMaterialId = mesh_info[2]
			indices_buffer_offset, indices_buffer_count, indices_size, vertices_buffer_offset, vertices_buffer_size = mesh_properties

			#getting the vertex properties
			vertex_size = 0
			semantic_properties = []
			vertex_properties = []

			mMaterialId = mesh_info[2]
			for material in materials:
				if material[0] == mMaterialId:
					mShaderId = material[1][0]
					shader_description = material[1][1]
					for shader in shaders:
						if shader[0] == mShaderId:
							vertex_properties = shader[9]
							break
					break

			if vertex_properties == []:
				print("WARNING: failed to get vertex properties of mesh %d of renderable '%s'. Ignoring it." % (mesh_index, mRenderableId))
				continue

			vertex_size = vertex_properties[0]
			semantic_properties = vertex_properties[1][0]

			f.seek(indices_buffer_offset, 0)

			mesh_indices = []

			tristrip_indices = []
			if indices_size == 4:
				indices_type = "I"
				terminator = 0xFFFFFFFF
			else:
				indices_type = "H"
				terminator = 0xFFFF

			for i in range(0, indices_buffer_count):
				index = struct.unpack("<%s" % (indices_type), f.read(indices_size))[0]
				if index != terminator and index >= vertices_buffer_size/vertex_size:
					continue

				tristrip_indices.append(index)

			for index in tristrip_indices:
				if index in mesh_indices:
					continue
				if index == terminator:
					continue
				mesh_indices.append(index)

			indices_buffer[mesh_index] = get_triangle_from_trianglestrip(tristrip_indices, vertices_buffer_size/vertex_size)

			padding = calculate_padding(f.tell(), 0x10)
			if padding == 0:
				padding = 0x10

			min_mesh_index = struct.unpack("<%s%s" % (padding // indices_size, indices_type), f.read(padding))[0]

			#getting the vertex properties
			# vertex_size = 0
			# semantic_properties = []
			# vertex_properties = []

			# mMaterialId = mesh_info[2]
			# for material in materials:
				# if material[0] == mMaterialId:
					# mShaderId = material[1][0]
					# for shader in shaders:
						# if shader[0] == mShaderId:
							# vertex_properties = shader[9]
							# break
					# break

			# if vertex_properties == []:
				# print("WARNING: failed to get vertex properties of mesh %d of renderable '%s'. Ignoring it." % (mesh_index, mRenderableId))
				# continue

			# vertex_size = vertex_properties[0]
			# semantic_properties = vertex_properties[1][0]

			semantic_types = []
			semantic_data_types = []
			for semantic in semantic_properties:
				semantic_types.append(semantic[0])
				semantic_data_types.append(semantic[1][0])

			mesh_vertices_buffer = []

			f.seek(vertices_buffer_offset, 0)
			for index in mesh_indices:
				position = []
				normal = []
				normal2 = []
				color = []
				color2 = []
				tangent = []
				uv1 = []
				uv2 = []
				uv3 = []
				uv4 = []
				uv5 = []
				uv6 = []
				blend_indices = []
				blend_weight = []
				for semantic in semantic_properties:
					f.seek(vertices_buffer_offset + index*vertex_size, 0)

					#semantic = [semantic_type, data_type, data_offset]
					semantic_type = semantic[0]
					data_type = semantic[1]
					data_offset = semantic[2]

					f.seek(data_offset, 1)
					if data_type[0][-1] == "e":
						values = frombuffer(f.read(data_type[1]), dtype="<%s" % data_type[0][-1])	#np.frombuffer
					elif "norm" in data_type[0]:
						data_type_ = data_type[0].replace("norm", "")
						values = struct.unpack("<%s" % data_type_, f.read(data_type[1]))
						#scale = 10.0
						scale = 8.0
						values = [values[0]/values[3] * scale, values[1]/values[3] * scale, values[2]/values[3] * scale]
					else:
						values = struct.unpack("<%s" % data_type[0], f.read(data_type[1]))

					if semantic_type == "POSITION":
						position = values
					elif semantic_type == "POSITIONT":
						pass
					elif semantic_type == "NORMAL":
						normal = values
					elif semantic_type == "COLOR":
						color = values
					elif semantic_type == "TEXCOORD1":
						uv1 = values
					elif semantic_type == "TEXCOORD2":
						uv2 = values
					elif semantic_type == "TEXCOORD3":
						uv3 = values
					elif semantic_type == "TEXCOORD4":
						uv4 = values
					elif semantic_type == "TEXCOORD5":
						if data_type[0] == "2e":
							uv5 = values
						elif data_type[0] == "3f":
							normal2 = values
					elif semantic_type == "TEXCOORD6":
						uv6 = values
					elif semantic_type == "TEXCOORD7":
						pass
					elif semantic_type == "TEXCOORD8":
						pass
					elif semantic_type == "BLENDINDICES":
						blend_indices = values
					elif semantic_type == "BLENDWEIGHT":
						blend_weight = values
					elif semantic_type == "TANGENT":
						tangent = values
					elif semantic_type == "BINORMAL":
						pass
					elif semantic_type == "COLOR2":
						pass
					elif semantic_type == "PSIZE":
						pass

				if normal == [] and normal2 != []:
					normal = normal2[:]

				sensors_list.extend(blend_indices[0:2])
				if resource_type == "CharacterSpec" or resource_type == "InstanceList":
					sensors_list.extend(blend_indices[2:4])
				else:
					bones_list.extend(blend_indices[2:4])

				mesh_vertices_buffer.append([index, position, normal, tangent, color, uv1, uv2, uv3, uv4, uv5, uv6, blend_indices, blend_weight, color2])

			vertices_buffer[mesh_index] = [semantic_types, mesh_vertices_buffer, semantic_data_types, shader_description]

	sensors_list = sorted(set(sensors_list))
	bones_list = sorted(set(bones_list))

	#==================================================================================================
	#Building Mesh
	#==================================================================================================
	me_ob = bpy.data.meshes.new(mRenderableId)
	obj = bpy.data.objects.new(mRenderableId, me_ob)

	#Get a BMesh representation
	bm = bmesh.new()

	#Creating new properties
	blend_index1 = (bm.verts.layers.int.get("blend_index1") or bm.verts.layers.int.new('blend_index1'))
	blend_index2 = (bm.verts.layers.int.get("blend_index2") or bm.verts.layers.int.new('blend_index2'))
	blend_index3 = (bm.verts.layers.int.get("blend_index3") or bm.verts.layers.int.new('blend_index3'))
	blend_index4 = (bm.verts.layers.int.get("blend_index4") or bm.verts.layers.int.new('blend_index4'))

	blend_weight1 = (bm.verts.layers.float.get("blend_weight1") or bm.verts.layers.float.new('blend_weight1'))
	blend_weight2 = (bm.verts.layers.float.get("blend_weight2") or bm.verts.layers.float.new('blend_weight2'))
	blend_weight3 = (bm.verts.layers.float.get("blend_weight3") or bm.verts.layers.float.new('blend_weight3'))
	blend_weight4 = (bm.verts.layers.float.get("blend_weight4") or bm.verts.layers.float.new('blend_weight4'))

	#Color layer
	color_layer = (bm.loops.layers.color.get("VColor1") or bm.loops.layers.color.new("VColor1"))

	#Blend weights layer (deform layer)
	dl = bm.verts.layers.deform.verify()

	#Creating vertex groups
	for index in sensors_list:
		vgroup = obj.vertex_groups.new(name = "Sensor_%03d" % index)

	for index in bones_list:
		vgroup = obj.vertex_groups.new(name = "Bone_%03d" % index)

	vert_indices = [[] for _ in range(num_meshes)]
	normal_data = []
	has_some_normal_data = False
	vgroups = []

	for mesh_info in meshes_info:
		mesh_index = mesh_info[0]
		mMaterialId = mesh_info[-1]
		indices = indices_buffer[mesh_index]
		semantic_types, mesh_vertices_buffer, semantic_data_types, shader_description = vertices_buffer[mesh_index]

		#add material to the mesh list of materials
		me_ob.materials.append(bpy.data.materials.get(mMaterialId))

		BMVert_dictionary = {}

		# uvName = "UVMap"
		# uv_layer = bm.loops.layers.uv.get(uvName) or bm.loops.layers.uv.new(uvName)
		# uvName = "UV2Map"
		# uv2_layer = bm.loops.layers.uv.get(uvName) or bm.loops.layers.uv.new(uvName)
		# uvName = "UV3Map"
		# uv3_layer = bm.loops.layers.uv.get(uvName) or bm.loops.layers.uv.new(uvName)
		# uvName = "UV4Map"
		# uv4_layer = bm.loops.layers.uv.get(uvName) or bm.loops.layers.uv.new(uvName)
		# uvName = "UV5Map"
		# uv5_layer = bm.loops.layers.uv.get(uvName) or bm.loops.layers.uv.new(uvName)
		# uvName = "UV6Map"
		# uv6_layer = bm.loops.layers.uv.get(uvName) or bm.loops.layers.uv.new(uvName)

		semantic_type = "TEXCOORD1"
		if semantic_type in semantic_types and semantic_data_types[semantic_types.index(semantic_type)][0] == "2":		 #2f, 2e, 2h,...
			uvName = "UVMap" #or UV1Map
			uv_layer = bm.loops.layers.uv.get(uvName) or bm.loops.layers.uv.new(uvName)

		semantic_type = "TEXCOORD2"
		if semantic_type in semantic_types and semantic_data_types[semantic_types.index(semantic_type)][0] == "2":
			uvName = "UV2Map"
			uv2_layer = bm.loops.layers.uv.get(uvName) or bm.loops.layers.uv.new(uvName)

		semantic_type = "TEXCOORD3"
		if semantic_type in semantic_types and semantic_data_types[semantic_types.index(semantic_type)][0] == "2":
			uvName = "UV3Map"
			uv3_layer = bm.loops.layers.uv.get(uvName) or bm.loops.layers.uv.new(uvName)

		semantic_type = "TEXCOORD4"
		if semantic_type in semantic_types and semantic_data_types[semantic_types.index(semantic_type)][0] == "2":
			uvName = "UV4Map"
			uv4_layer = bm.loops.layers.uv.get(uvName) or bm.loops.layers.uv.new(uvName)

		semantic_type = "TEXCOORD5"
		if semantic_type in semantic_types and semantic_data_types[semantic_types.index(semantic_type)][0] == "2":
			uvName = "UV5Map"
			uv5_layer = bm.loops.layers.uv.get(uvName) or bm.loops.layers.uv.new(uvName)

		semantic_type = "TEXCOORD6"
		if semantic_type in semantic_types and semantic_data_types[semantic_types.index(semantic_type)][0] == "2":
			uvName = "UV6Map"
			uv6_layer = bm.loops.layers.uv.get(uvName) or bm.loops.layers.uv.new(uvName)

		for vertex_data in mesh_vertices_buffer:
			index, position, normal, tangent, color, uv1, uv2, uv3, uv4, uv5, uv6, blend_indices, blend_weight, color2 = vertex_data
			BMVert = bm.verts.new(position)
			BMVert.index = index
			BMVert_dictionary[index] = [BMVert, uv1, uv2, uv3, uv4, uv5, uv6, color, color2]
			vert_indices[mesh_index].append(BMVert.index)

			if "NORMAL" in semantic_types:
				BMVert.normal = normal
				normal_data.append([index, normal])
				if has_some_normal_data == False:
					me_ob.create_normals_split()
				has_some_normal_data = True
			elif "TEXCOORD5" in semantic_types and (semantic_data_types[semantic_types.index("TEXCOORD5")] == "4hnorm" or semantic_data_types[semantic_types.index("TEXCOORD5")] == "3f"):
				BMVert.normal = normal
				normal_data.append([index, normal])
				if has_some_normal_data == False:
					me_ob.create_normals_split()
				has_some_normal_data = True
			else:
				normal_data.append([index, (0.0, 0.0, 0.0)])

			if "BLENDINDICES" in semantic_types:
				BMVert[blend_index1] = blend_indices[0]
				BMVert[blend_index2] = blend_indices[1]
				BMVert[blend_index3] = blend_indices[2]
				BMVert[blend_index4] = blend_indices[3]

			if "BLENDWEIGHT" in semantic_types:
				BMVert[blend_weight1] = blend_weight[0]*100.0/255.0
				BMVert[blend_weight2] = blend_weight[1]*100.0/255.0
				BMVert[blend_weight3] = blend_weight[2]*100.0/255.0
				BMVert[blend_weight4] = blend_weight[3]*100.0/255.0

			if "BLENDINDICES" in semantic_types and "BLENDWEIGHT" in semantic_types:
				vgroup_name_previous = []
				for i in range(0, 4):
					if i <= 1 or resource_type == "CharacterSpec" or resource_type == "InstanceList":
						vgroup_name = "Sensor_%03d" % blend_indices[i]
					else:
						vgroup_name = "Bone_%03d" % blend_indices[i]

					if vgroup_name in vgroup_name_previous:
						continue
					vgroup_name_previous.append(vgroup_name)

					for vgroup in obj.vertex_groups:
						if vgroup.name == vgroup_name:
							BMVert[dl][vgroup.index] = blend_weight[i]/255.0
							break

		for i, face in enumerate(indices):
			face_vertices = [BMVert_dictionary[face[0]][0], BMVert_dictionary[face[1]][0], BMVert_dictionary[face[2]][0]]
			BMFace = bm.faces.get(face_vertices) or bm.faces.new(face_vertices)
			if BMFace.index != -1:
				BMFace = BMFace.copy(verts=False, edges=False)
			BMFace.index = i
			BMFace.smooth = True
			#BMFace.material_index = me_ob.materials.find(mMaterialId)	#issue with duplicated materials
			BMFace.material_index = mesh_index

			if "TEXCOORD1" in semantic_types:
				for index, loop in enumerate(BMFace.loops):
					loop[uv_layer].uv = [BMVert_dictionary[loop.vert.index][1][0], 1.0 - BMVert_dictionary[loop.vert.index][1][1]]
			if "TEXCOORD2" in semantic_types:
				for index, loop in enumerate(BMFace.loops):
					loop[uv2_layer].uv = [BMVert_dictionary[loop.vert.index][2][0], 1.0 - BMVert_dictionary[loop.vert.index][2][1]]
			if "TEXCOORD3" in semantic_types:
				for index, loop in enumerate(BMFace.loops):
					loop[uv3_layer].uv = [BMVert_dictionary[loop.vert.index][3][0], 1.0 - BMVert_dictionary[loop.vert.index][3][1]]
			if "TEXCOORD4" in semantic_types:
				for index, loop in enumerate(BMFace.loops):
					loop[uv4_layer].uv = [BMVert_dictionary[loop.vert.index][4][0], 1.0 - BMVert_dictionary[loop.vert.index][4][1]]
			if "TEXCOORD5" in semantic_types and semantic_data_types[semantic_types.index("TEXCOORD5")] == "2e":
				for index, loop in enumerate(BMFace.loops):
					loop[uv5_layer].uv = [BMVert_dictionary[loop.vert.index][5][0], 1.0 - BMVert_dictionary[loop.vert.index][5][1]]
			if "TEXCOORD6" in semantic_types:
				for index, loop in enumerate(BMFace.loops):
					loop[uv6_layer].uv = [BMVert_dictionary[loop.vert.index][6][0], 1.0 - BMVert_dictionary[loop.vert.index][6][1]]

			if "COLOR" in semantic_types:
				for index, loop in enumerate(BMFace.loops):
					color = BMVert_dictionary[loop.vert.index][7][:]
					loop[color_layer] = [color[0]/255.0, color[1]/255.0, color[2]/255.0, color[3]/255.0]

		if shader_description in ("Foliage_LargeSprites_Proto", "Foliage_LargeSprites_Proto_Spec_Normal", "Foliage_Proto", "Foliage_Proto_Spec_Normal"):
			mat = bpy.data.materials.get(mMaterialId)

			if "QuadSize" in mat:
				QuadSize = mat["QuadSize"]

				modifier_name = 'scale_%s' % mMaterialId
				if modifier_name in bpy.data.node_groups:
					node_group = bpy.data.node_groups.get(modifier_name)
				else:
					node_group = bpy.data.node_groups.new(modifier_name, 'GeometryNodeTree')

					input_node = node_group.nodes.new(type='NodeGroupInput')
					output_node = node_group.nodes.new(type='NodeGroupOutput')
					material_node = node_group.nodes.new(type='GeometryNodeInputMaterial')
					material_selection_node = node_group.nodes.new(type='GeometryNodeMaterialSelection')
					scale_elements_node = node_group.nodes.new(type='GeometryNodeScaleElements')

					node_group.outputs.new('NodeSocketGeometry', 'Geometry')
					node_group.inputs.new('NodeSocketGeometry', 'Geometry')

					material_node.material = mat
					scale_elements_node.inputs[2].default_value = QuadSize[0]

					node_group.links.new(material_node.outputs[0], material_selection_node.inputs[0])

					node_group.links.new(input_node.outputs[0], scale_elements_node.inputs[0])
					node_group.links.new(material_selection_node.outputs[0], scale_elements_node.inputs[1])

					node_group.links.new(scale_elements_node.outputs[0], output_node.inputs[0])

				modifier = obj.modifiers.new("scale_modifier", "NODES")
				try:
					bpy.data.node_groups.remove(modifier.node_group)
				except:
					pass
				modifier.node_group = node_group


	#Finish up, write the bmesh back to the mesh
	bm.to_mesh(me_ob)
	bm.free()

	try:
		if resource_type == "GraphicsSpec":
			me_ob.color_attributes.active_color_index = 0
		elif resource_type == "CharacterSpec":
			me_ob.color_attributes.active_color_index = 0
		elif resource_type == "InstanceList":
			me_ob.color_attributes.active_color_index = 0
	except:
		if resource_type == "GraphicsSpec":
			me_ob.vertex_colors.active_index = 0
		elif resource_type == "CharacterSpec":
			me_ob.vertex_colors.active_index = 0
		elif resource_type == "InstanceList":
			me_ob.vertex_colors.active_index = 0

	if has_some_normal_data:
		temp = []
		for data in normal_data:
			temp.append(data[1])
		normal_data = temp[:]

		me_ob.validate(clean_customdata=False)
		me_ob.normals_split_custom_set_from_vertices( normal_data )
		me_ob.use_auto_smooth = True
	else:
		me_ob.calc_normals()

	return obj


def create_texture(texture_path, texture_properties): # OK
	file, ext = os.path.splitext(texture_path)
	if ext == ".dds":
		return texture_path

	texture_body = file + "_texture" + ext
	texture_path = file + ".dds"

	with open(texture_path, "wb") as f:
		# remap, pitch, storeFlags
		format, width, height, depth, dimension, main_mipmap, mipMapCount, unknown_0x20 = texture_properties

		#struct DDS_PIXELFORMAT
		# {
			# uint32  size;
			# uint32  flags;
			# uint32  fourCC;
			# uint32  RGBBitCount;
			# uint32  RBitMask;
			# uint32  GBitMask;
			# uint32  BBitMask;
			# uint32  ABitMask;
		# };


		# https://docs.microsoft.com/en-us/windows/win32/direct3ddds/dds-header
		# https://docs.microsoft.com/en-us/windows/win32/direct3ddds/dds-pixelformat

		DDS_MAGIC = 0x20534444
		header_size = 0x7C
		caps3 = 0
		caps4 = 0
		reserved1 = 0
		reserved2 = 0
		compressed = True
		cubemap = False
		alpha = False
		pitch = True

		if "DXT" in format:
			dwFourCC = format
			dwRGBBitCount = 0
			dwRBitMask = 0
			dwGBitMask = 0
			dwBBitMask = 0
			dwABitMask = 0
		elif format == "B8G8R8A8":
			alpha = True
			compressed = False
			dwRGBBitCount = 32
			dwRBitMask = 0xFF0000
			dwGBitMask = 0xFF00
			dwBBitMask = 0xFF
			dwABitMask = 0xFF000000
		elif format == "R8G8B8A8":
			alpha = True
			compressed = False
			dwRGBBitCount = 32
			dwRBitMask = 0xFF
			dwGBitMask = 0xFF00
			dwBBitMask = 0xFF0000
			dwABitMask = 0xFF000000
		elif format == "A8R8G8B8":
			alpha = True
			compressed = False
			dwRGBBitCount = 32
			dwRBitMask = 0xFF00
			dwGBitMask = 0xFF0000
			dwBBitMask = 0xFF000000
			dwABitMask = 0xFF
		else:
			alpha = True
			compressed = False
			dwRGBBitCount = 32
			dwRBitMask = 0xFF0000
			dwGBitMask = 0xFF00
			dwBBitMask = 0xFF
			dwABitMask = 0xFF000000

		# block-compressed
		block_size = 16
		if format == "DXT1" or format == "BC1" or format == "BC4":
			block_size = 8
		pitchOrLinearSize = max( 1, int((width+3)/4) ) * block_size

		# Flags
		DDSD_CAPS = 0x1
		DDSD_HEIGHT = 0x2
		DDSD_WIDTH = 0x4
		DDSD_PITCH = 0x8
		DDSD_PIXELFORMAT = 0x1000
		DDSD_MIPMAPCOUNT = 0x20000
		DDSD_LINEARSIZE = 0x80000
		DDSD_DEPTH = 0x800000

		flags = DDSD_CAPS + DDSD_HEIGHT + DDSD_WIDTH
		flags += DDSD_PIXELFORMAT
		if mipMapCount > 0:
			flags += DDSD_MIPMAPCOUNT
		if compressed == False and pitch:
			flags += DDSD_PITCH
		if compressed and pitch:
			flags += DDSD_LINEARSIZE
		if depth > 1:
			flags += DDSD_DEPTH

		# DDS pixel format
		dwSize = 32

		DDPF_ALPHAPIXELS = 0x1
		DDPF_ALPHA = 0x2
		DDPF_FOURCC = 0x4
		DDPF_RGB = 0x40
		DDPF_YUV = 0x200
		DDPF_LUMINANCE = 0x20000
		dwFlags = 0

		if alpha:
			dwFlags += DDPF_ALPHAPIXELS
		if alpha and compressed: #compressed == False
			dwFlags += DDPF_ALPHA
		if compressed:
			dwFlags += DDPF_FOURCC
		if compressed == False:
			dwFlags += DDPF_RGB

		# Caps flags
		DDSCAPS_COMPLEX = 0x8
		DDSCAPS_MIPMAP = 0x400000
		DDSCAPS_TEXTURE = 0x1000
		caps = DDSCAPS_TEXTURE
		if mipMapCount > 0 or depth > 1 or cubemap:
			caps += DDSCAPS_COMPLEX
		if mipMapCount > 0:
			caps += DDSCAPS_MIPMAP

		# Caps2 flags
		DDSCAPS2_CUBEMAP = 0x200
		DDSCAPS2_CUBEMAP_POSITIVEX = 0x400
		DDSCAPS2_CUBEMAP_NEGATIVEX = 0x800
		DDSCAPS2_CUBEMAP_POSITIVEY = 0x1000
		DDSCAPS2_CUBEMAP_NEGATIVEY = 0x2000
		DDSCAPS2_CUBEMAP_POSITIVEZ = 0x4000
		DDSCAPS2_CUBEMAP_NEGATIVEZ = 0x8000
		DDSCAPS2_VOLUME = 0x200000
		caps2 = 0x0
		if cubemap:
			caps2 += DDSCAPS2_CUBEMAP
			caps2 += DDSCAPS2_CUBEMAP_POSITIVEX + DDSCAPS2_CUBEMAP_NEGATIVEX
			caps2 += DDSCAPS2_CUBEMAP_POSITIVEY + DDSCAPS2_CUBEMAP_NEGATIVEY
			caps2 += DDSCAPS2_CUBEMAP_POSITIVEZ + DDSCAPS2_CUBEMAP_NEGATIVEZ
		if dimension == 3:
			caps2 += DDSCAPS2_VOLUME

		f.write(struct.pack("<I", DDS_MAGIC))			#OK
		f.write(struct.pack("<I", header_size))			#OK
		f.write(struct.pack("<I", flags))
		f.write(struct.pack("<I", height))				#OK
		f.write(struct.pack("<I", width))				#OK
		f.write(struct.pack("<I", pitchOrLinearSize))   #OK
		f.write(struct.pack("<I", depth))	#only if DDS_HEADER_FLAGS_VOLUME is set in flags
		f.write(struct.pack("<I", mipMapCount))			#OK
		f.write(struct.pack("<11I", *[reserved1]*11))   #OK

		# DDS_PIXELFORMAT
		f.write(struct.pack("<I", dwSize))
		f.write(struct.pack("<I", dwFlags))
		if compressed:
			f.write(dwFourCC.encode())
		else:
			f.write(struct.pack("<I", 0))
		f.write(struct.pack("<I", dwRGBBitCount))
		f.write(struct.pack("<I", dwRBitMask))
		f.write(struct.pack("<I", dwGBitMask))
		f.write(struct.pack("<I", dwBBitMask))
		f.write(struct.pack("<I", dwABitMask))

		f.write(struct.pack("<I", caps))
		f.write(struct.pack("<I", caps2))
		f.write(struct.pack("<I", caps3))               #OK
		f.write(struct.pack("<I", caps4))               #OK
		f.write(struct.pack("<I", reserved2))           #OK

		with open(texture_body, "rb") as g:
			f.write(g.read())

	return texture_path


def create_polygonsoup(polygonsoup_object_name, PolygonSoupVertices, PolygonSoupPolygons, mabVertexOffsetMultiply, miVertexOffsetConstant, mfComprGranularity, resource_type, track_unit_number): # OK
	me_ob = bpy.data.meshes.new(polygonsoup_object_name)
	obj = bpy.data.objects.new(polygonsoup_object_name, me_ob)

	bm = bmesh.new()

	#Creating new properties
	edge_cosine1 = (bm.faces.layers.int.get("edge_cosine1") or bm.faces.layers.int.new('edge_cosine1'))
	edge_cosine2 = (bm.faces.layers.int.get("edge_cosine2") or bm.faces.layers.int.new('edge_cosine2'))
	edge_cosine3 = (bm.faces.layers.int.get("edge_cosine3") or bm.faces.layers.int.new('edge_cosine3'))
	edge_cosine4 = (bm.faces.layers.int.get("edge_cosine4") or bm.faces.layers.int.new('edge_cosine4'))
	#collision_tag0 = (bm.faces.layers.int.get("collision_tag0") or bm.faces.layers.int.new('collision_tag0'))
	collision_tag1 = (bm.faces.layers.int.get("collision_tag1") or bm.faces.layers.int.new('collision_tag1'))

	#mAabbMin = PolySoupBox[0]
	#minX = min([vertex[0] for vertex in PolygonSoupVertices])
	#minY = min([vertex[1] for vertex in PolygonSoupVertices])
	#minZ = min([vertex[2] for vertex in PolygonSoupVertices])
	#minVertex = [minX, minY, minZ]

	BMVert_dictionary = {}
	for i, vertex in enumerate(PolygonSoupVertices):
		for j in range(0, 3):
			mbVertexOffsetMultiply = mabVertexOffsetMultiply[j]
			#vertex[j] = vertex[j] + mAabbMin[j]/mfComprGranularity - minVertex[j]
			#vertex[j] = vertex[j] + mbVertexOffsetMultiply*miVertexOffsetConstant/mfComprGranularity
			vertex[j] = vertex[j]*mfComprGranularity + mbVertexOffsetMultiply*miVertexOffsetConstant

		BMVert = bm.verts.new(vertex)
		BMVert.index = i
		BMVert_dictionary[i] = BMVert

	for i, face in enumerate(PolygonSoupPolygons):
		muCollisionTag, mau8VertexIndices, mau8EdgeCosines = face
		mu16CollisionTag_part0, mu16CollisionTag_part1 = muCollisionTag

		if len(mau8VertexIndices) != len(set(mau8VertexIndices)):
			print("WARNING: collision face has duplicated vertices:", mau8VertexIndices)
			mau8VertexIndices = tuple(dict.fromkeys(mau8VertexIndices))
			print("adjusting to", mau8VertexIndices)

		if len(mau8VertexIndices) == 4:
			face_vertices = [BMVert_dictionary[mau8VertexIndices[0]], BMVert_dictionary[mau8VertexIndices[1]], BMVert_dictionary[mau8VertexIndices[3]], BMVert_dictionary[mau8VertexIndices[2]]]
		elif len(mau8VertexIndices) == 3:
			face_vertices = [BMVert_dictionary[mau8VertexIndices[0]], BMVert_dictionary[mau8VertexIndices[1]], BMVert_dictionary[mau8VertexIndices[2]]]
		else:
			print("WARNING: polygon vertices do not form a face. Skipping it.")
			continue

		BMFace = bm.faces.get(face_vertices) or bm.faces.new(face_vertices)
		if BMFace.index != -1:
			BMFace0 = BMFace
			BMFace = BMFace.copy(verts=False, edges=False)

			original_face_indices = [vert.index for vert in BMFace.verts]
			new_face_indices = [vert.index for vert in face_vertices]
			same_winding_faces_as_original = [original_face_indices[-n:] + original_face_indices[:-n] for n in range(0, len(original_face_indices))]
			if new_face_indices not in same_winding_faces_as_original:
				BMFace.normal_flip()

		BMFace.index = i
		BMFace[edge_cosine1] = mau8EdgeCosines[0]
		BMFace[edge_cosine2] = mau8EdgeCosines[1]
		BMFace[edge_cosine3] = mau8EdgeCosines[2]
		BMFace[edge_cosine4] = mau8EdgeCosines[3]
		#BMFace[collision_tag0] = mu16CollisionTag_part0
		if resource_type == "InstanceList":
			BMFace[collision_tag1] = mu16CollisionTag_part1 - track_unit_number*0x10
		elif resource_type == "PolygonSoupList" and track_unit_number != None:
			BMFace[collision_tag1] = mu16CollisionTag_part1 - track_unit_number*0x10
		else:
			BMFace[collision_tag1] = mu16CollisionTag_part1

		#material_name = str(hex(mu16CollisionTag_part1))[2:].zfill(4).upper()
		material_name = str(hex(mu16CollisionTag_part0))[2:].zfill(4).upper()
		mat = bpy.data.materials.get(material_name)
		if mat == None:
			mat = bpy.data.materials.new(material_name)
			mat.use_nodes = True
			mat.name = material_name

		if mat.name not in me_ob.materials:
			me_ob.materials.append(mat)

		BMFace.material_index = me_ob.materials.find(mat.name)

	bm.to_mesh(me_ob)
	bm.free()

	return obj


def create_zone(muZoneId, zonepoints, muDistrictId, RGBA_random_district, resource_version):
	if resource_version == "NFSHPR_PC":
		zone_object_name = "Zone_%04d.NFSHPR" % muZoneId
	elif resource_version == "NFSHP_PC":
		zone_object_name = "Zone_%04d.NFSHP" % muZoneId

	me_ob = bpy.data.meshes.new(zone_object_name)
	obj = bpy.data.objects.new(zone_object_name, me_ob)

	bm = bmesh.new()
	BMVert_dictionary = {}

	for i, zonepoint in enumerate(zonepoints):
		BMVert = bm.verts.new((zonepoint[0], 0.0, zonepoint[1]))
		BMVert.index = i
		BMVert_dictionary[i] = BMVert

	BMFace = bm.faces.new(BMVert_dictionary.values())

	material_name = str(muDistrictId)
	mat = bpy.data.materials.get(material_name)
	if mat == None:
		mat = bpy.data.materials.new(material_name)
		mat.use_nodes = True
		mat.name = material_name
		if mat.node_tree.nodes[0].bl_idname != "ShaderNodeOutputMaterial":
			mat.node_tree.nodes[0].name = material_name
		mat.node_tree.nodes[material_name].inputs['Base Color'].default_value = RGBA_random_district

	if mat.name not in me_ob.materials:
		me_ob.materials.append(mat)

	BMFace.material_index = me_ob.materials.find(mat.name)

	bm.to_mesh(me_ob)
	bm.free()

	return obj


def create_sphere(name="dgi_sphere", radius=1.0):
	# Create an empty mesh and the object.
	me_ob = bpy.data.meshes.new(name)
	obj = bpy.data.objects.new(name, me_ob)

	# Construct the bmesh sphere and assign it to the blender mesh.
	bm = bmesh.new()
	bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=8, radius=radius)
	for f in bm.faces:
		f.smooth = True
	bm.to_mesh(me_ob)
	bm.free()

	return obj


def convert_texture_to_dxt5(raster_path, make_backup):
	if make_backup == True:
		shutil.copy2(raster_path, raster_path + ".bak")
	out_raster_path = os.path.splitext(raster_path)[0] + ".dds"
	nvidia_path = nvidiaGet()

	compress_type = "bc3" # DXT5

	os.system('"%s -alpha -%s -silent "%s" "%s""' % (nvidia_path, compress_type, raster_path, out_raster_path))

	return out_raster_path


def get_triangle_from_trianglestrip(TriStrip, vertices_count):
	indices_buffer = []
	cte = 0
	for i in range(2, len(TriStrip)):
		if TriStrip[i] == 65535 or TriStrip[i-1] == 65535 or TriStrip[i-2] == 65535:
			if i%2==0:
				cte = -1
			else:
				cte = 0
			pass
		else:
			if (i+cte)%2==0:
				a = TriStrip[i-2]
				b = TriStrip[i-1]
				c = TriStrip[i]
			else:
				a = TriStrip[i-1]
				b = TriStrip[i-2]
				c = TriStrip[i]
			if a != b and b != c and c != a:
				if (a < vertices_count) and (b < vertices_count) and (c < vertices_count):
					indices_buffer.append([a, b, c])

	# indices = TriStrip[:]
	# indices_buffer = []
	# def alternate(is_even, xs):
		# return xs if is_even else (xs[0], xs[2], xs[1])

	# terminator = 0xFFFF
	# is_even = False
	# i = 0
	# while i < len(indices) - 2:
		# triangle = (indices[i], indices[i + 1], indices[i + 2])

		# if terminator in triangle:
			# is_even = True
			# i += 3
			# continue

		# triangle = alternate(is_even, triangle)

		# is_even = not is_even
		# i += 1

		# if len(set(triangle)) < len(triangle):
			# # It is a degenerated triangle
			# continue
		# if any(index >= vertices_count for index in triangle):
			# continue

		# indices_buffer.append(triangle)

	return indices_buffer


def get_vertex_semantic(semantic_type): # OK
	semantics = ["", "POSITION", "POSITIONT", "NORMAL", "COLOR",
				 "TEXCOORD1", "TEXCOORD2", "TEXCOORD3", "TEXCOORD4", "TEXCOORD5", "TEXCOORD6", "TEXCOORD7", "TEXCOORD8",
				 "BLENDINDICES", "BLENDWEIGHT", "TANGENT", "BINORMAL", "COLOR2", "PSIZE"]
	# semantics = ["", "POSITION", "POSITIONT", "NORMAL", "COLOR",
				 # "TEXCOORD1", "TEXCOORD2", "TEXCOORD3", "TEXCOORD4", "NORMAL_PACKED", "UNKNOWN_0xA", "TEXCOORD7", "TEXCOORD8",
				 # "BLENDINDICES", "BLENDWEIGHT", "TANGENT", "BINORMAL", "COLOR2", "PSIZE"]

	return semantics[semantic_type]


def get_vertex_data_type(data_type):
	data_types = {2 : ["4f", 0x10],
				  3 : ["4I", 0x10],
				  4 : ["4i", 0x10],
				  6 : ["3f", 0xC],
				  7 : ["3I", 0xC],
				  8 : ["3i", 0xC],
				  10 : ["4e", 0x8], # numpy
				  11 : ["4H", 0x8], #normalized
				  12 : ["4I", 0x10],
				  #13 : ["4h", 0x8], #normalized
				  13 : ["4hnorm", 0x8], #normalized
				  14 : ["4i", 0x10],
				  16 : ["2f", 0x8],
				  17 : ["2I", 0x8],
				  18 : ["2i", 0x8],
				  28 : ["4B", 0x4], #normalized
				  30 : ["4B", 0x4],
				  32 : ["4b", 0x4],
				  34 : ["2e", 0x4],
				  35 : ["2H", 0x4], #normalized
				  36 : ["2H", 0x4],
				  37 : ["2h", 0x4], #normalized
				  38 : ["2h", 0x4],
				  40 : ["1f", 0x4],
				  41 : ["1f", 0x4],
				  42 : ["1I", 0x4],
				  43 : ["1i", 0x4],
				  49 : ["2B", 0x2], #normalized
				  50 : ["2B", 0x2],
				  51 : ["2b", 0x2], #normalized
				  52 : ["2b", 0x2],
				  54 : ["1e", 0x2],
				  57 : ["1H", 0x2],
				  59 : ["1h", 0x2],
				  61 : ["1B", 0x1], #normalized
				  62 : ["1B", 0x1],
				  63 : ["1b", 0x1], #normalized
				  64 : ["1b", 0x1]}

	return data_types[data_type]


def get_vertex_semantic_d3d9(semantic_type):
	semantics = ["", "POSITION", "POSITIONT", "NORMAL", "COLOR", "COLOR2",
				 "TEXCOORD1", "TEXCOORD2", "TEXCOORD3", "TEXCOORD4", "TEXCOORD5", "TEXCOORD6", "TEXCOORD7", "TEXCOORD8",
				 "BLENDINDICES", "BLENDWEIGHT", "POSITION2", "NORMAL2", "POSITION3", "POSITION4", "POSITION5",
				 "TANGENT", "BINORMAL", "COLOR2", "FOG", "PSIZE", "BLENDINDICES2", "BLENDWEIGHT2"]

	return semantics[semantic_type]


def get_vertex_data_type_d3d9(data_type):
	data_types = {0 :  ["1f", 0x04],
				  1 :  ["2f", 0x08],
				  2 :  ["3f", 0x0C],
				  3 :  ["4f", 0x10],
				  4 :  ["4B", 0x4],
				  5 :  ["4B", 0x4],
				  6 :  ["2h", 0x4],
				  7 :  ["4h", 0x8],
				  8 :  ["4B", 0x4],
				  9 :  ["2h", 0x4],
				  10 : ["4hnorm", 0x8],
				  11 : ["2H", 0x4],
				  12 : ["4H", 0x8],
				  13 : ["3f", 0x4],
				  14 : ["3f", 0x4],
				  15 : ["2e", 0x4],
				  16 : ["4e", 0x8],
				  17 : ["", 0x0]}

	return data_types[data_type]


def get_raster_format(fourcc):
	format_from_fourcc = {	"B8G8R8A8" : 87, #21
							"R8G8B8A8" : 28,
							"A8R8G8B8" : 255,
							"DXT1" : 71,
							"DXT3" : 73,
							"DXT5" : 77}

	try:
		return format_from_fourcc[fourcc]
	except:
		print("WARNING: DXT compression not identified. Setting as 'R8G8B8A8'.")
		return 28


def get_fourcc(dxgi_format):
	fourcc = { 21 : "B8G8R8A8",
			   28 : "R8G8B8A8",
			   255 : "A8R8G8B8",
			   70 : "DXT1",
			   71 : "DXT1",
			   72 : "DXT1",
			   73 : "DXT3",
			   74 : "DXT3",
			   75 : "DXT3",
			   76 : "DXT5",
			   77 : "DXT5",
			   78 : "DXT5",
			   87 : "B8G8R8A8"}

	return fourcc[dxgi_format]


def get_random_color():
	#''' generate rgb using a list comprehension '''
	r, g, b = [random.random() for i in range(3)]
	return r, g, b, 1


def get_vehicle_name(Id):
	Vehicles = {97331:  'Lamborghini Murciélago LP 640',
				97352:  'Default',
				118158: 'Bugatti Veyron 16.4',
				118196: 'Porsche Boxster Spyder',
				118240: 'Bugatti Veyron 16.4',
				118393: 'Porsche Boxster Spyder',
				118454: 'Ford Shelby GT500',
				118492: 'Koenigsegg CCX',
				118530: 'Mitsubishi Lancer Evolution X',
				118570: 'Nissan GT-R SpecV (R35)',
				118608: 'Porsche Cayman S',
				118889: 'Audi R8 Coupé 5.2 FSI quattro',
				118940: 'Alfa Romeo 8C Spider',
				118984: 'Audi R8 Spyder 5.2 FSI quattro',
				121050: 'Lamborghini Murciélago LP 640',
				172237: 'Nissan 370Z (Z34)',
				172279: 'Koenigsegg CCXR Edition',
				172321: 'Lamborghini Gallardo LP 560-4',
				172363: 'Lamborghini Murciélago LP 670-4 SV',
				172460: 'McLaren F1',
				172502: 'Mercedes-Benz SLR McLaren 722 Edition',
				172544: 'Mercedes-Benz SLR McLaren Stirling Moss',
				172586: 'McLaren MP4-12C',
				172670: 'Mazda RX-8',
				172714: 'Subaru Impreza WRX STI',
				172756: 'BMW M6 Convertible',
				172798: 'Maserati Quattroporte Sport GT S',
				172840: 'Dodge Viper SRT10',
				172882: 'Dodge Viper SRT10 ACR',
				172966: 'BMW Z4 sDrive35is',
				210008: 'Audi R8 Coupé 5.2 FSI quattro',
				210456: 'Traffic Audi A4',
				210620: 'Traffic Porsche Cayenne Turbo',
				257578: 'Traffic Default',
				292004: 'BMW M3 E92',
				292069: 'Chevrolet Camaro SS',
				292146: 'Dodge Challenger SRT8',
				293008: 'Lamborghini Reventón',
				293124: 'Alfa Romeo 8C Competizione',
				293191: 'Ford GT',
				321070: 'Porsche 911 Targa 4S',
				329012: 'Mercedes-Benz SL65 AMG Black Series',
				329054: 'Porsche Panamera Turbo',
				329096: 'Porsche Carrera GT',
				345203: 'Ford Shelby GT500',
				345261: 'Pagani C9',
				380028: 'Audi TT RS Coupé',
				380071: 'Bugatti Veyron 16.4 Grand Sport',
				380114: 'Chevrolet Corvette Grand Sport',
				380157: 'Chevrolet Corvette Z06',
				380200: 'Chevrolet Corvette ZR1',
				380243: 'Ford Crown Victoria Police Interceptor',
				380286: 'Dodge Charger SRT8',
				380329: 'Ford Shelby GT500 Super Snake',
				380372: 'Ford Police Interceptor Concept',
				380415: 'Lamborghini Gallardo LP 550-2 Valentino Balboni',
				380501: 'Lamborghini Reventón Roadster',
				380544: 'Maserati GranCabrio',
				380587: 'Maserati GranTurismo S',
				380630: 'Pagani Zonda Cinque',
				380673: 'Pagani Zonda Cinque Roadster',
				380802: 'Porsche 911 GT3 RS',
				380845: 'Porsche 911 Turbo S Cabriolet',
				380888: 'Mercedes-Benz SLS AMG',
				380931: 'Nissan 370Z Roadster',
				380982: 'Aston Martin DBS',
				383026: 'Aston Martin DBS Volante',
				383069: 'Aston Martin V12 Vantage',
				383112: 'Bentley Continental Supersports Coupé',
				383155: 'Carbon Motors E7 Concept',
				383198: 'Jaguar XKR',
				383242: 'Koenigsegg CCX',
				383249: 'Lamborghini Gallardo Spyder LP 560-4',
				383297: 'Alfa Romeo 8C Competizione',
				383311: 'BMW M3 E92',
				383318: 'BMW Z4 sDrive35is',
				383326: 'Chevrolet Camaro SS',
				383333: 'Dodge Challenger SRT8',
				383340: 'Ford GT',
				383347: 'Lamborghini Gallardo LP 560-4',
				383354: 'Lamborghini Reventón',
				383361: 'McLaren F1',
				383375: 'Mercedes-Benz SLR McLaren 722 Edition',
				383382: 'Mitsubishi Lancer Evolution X',
				383389: 'Nissan GT-R SpecV (R35)',
				383396: 'Porsche 911 Targa 4S',
				383403: 'Porsche Cayman S',
				383410: 'Porsche Panamera Turbo',
				383425: 'McLaren MP4-12C',
				383432: 'Porsche 918 Spyder Concept Study',
				383480: 'Lamborghini Gallardo LP 570-4 Superleggera',
				383527: 'Aston Martin One-77',
				383613: 'Mazda RX-8',
				383620: 'Subaru Imprexa WRX STI',
				383627: 'Nissan 370Z',
				383641: 'Dodge Charger SRT8',
				383651: 'Alfa Romeo 8C Spider',
				383658: 'Aston Martin V12 Vantage',
				383665: 'Audi R8 Spyder 5.2 FSI quattro',
				383672: 'Nissan 370Z Roadster',
				383679: 'Bugatti Veyron 16.4 Grand Sport',
				383686: 'Porsche Carrera GT',
				383693: 'Porsche 911 GT3 RS',
				383700: 'Pagani Zonda Cinque Roadster',
				383707: 'Pagani Zonda Cinque',
				383714: 'Mercedes-Benz SL65 AMG Black Series',
				383721: 'Lamborghini Reventón Roadster',
				383728: 'Lamborghini Murciélago LP 670-4 SV',
				383735: 'Jaguar XKR',
				383742: 'Ford Shelby GT500 Super Snake',
				383749: 'Chevrolet Corvette Z06',
				383756: 'Chevrolet Corvette ZR1',
				383808: 'Koenigsegg Agera',
				383853: 'Lamborghini Gallardo LP 550-2 Valentino Balboni',
				459267: 'Traffic Ford Mustang GT500 Interceptor',
				459298: 'Traffic Infiniti G35',
				459784: 'Sphere Car',
				529328: 'Maserati GranCabrio',
				529376: 'Bentley Continental Supersports Coupé',
				529383: 'Pagani C9',
				529397: 'Audi TT RS Coupé',
				529411: 'Aston Martin DBS',
				529418: 'Aston Martin DBS Volante',
				529425: 'Aston Martin One-77',
				529432: 'BMW M6 Convertible',
				529446: 'Chevrolet Corvette Grand Sport',
				529453: 'Dodge Viper SRT10',
				529460: 'Dodge Viper SRT10 ACR',
				529481: 'Koenigsegg Agera',
				529488: 'Koenigsegg CCXR Edition',
				529502: 'Lamborghini Gallardo LP570-4 Superleggera',
				529509: 'Lamborghini Gallardo LP560-4 Spyder',
				529516: 'Maserati GranTurismo S',
				529523: 'Maserati Quattroporte Sport GT S',
				529530: 'Mercedes-Benz SLR McLaren Stirling Moss',
				529537: 'Mercedes-Benz SLS AMG',
				529544: 'Porsche 918 Spyder Concept Study',
				529551: 'Porsche 911 Turbo S Cabriolet',
				553242: 'Traffic Dodge Challenger',
				553384: 'Traffic Porsche Cayenne Turbo Cop',
				553409: 'Traffic Audi A3',
				553768: 'Traffic Chevrolet Express',
				607177: 'Traffic Dodge RAM 1500',
				607689: 'Traffic GMC TopKick',
				686357: 'Traffic Cadillac CTS-V',
				686399: 'Traffic Chevrolet Cobalt',
				686576: 'Traffic Dodge Grand Caravan',
				686663: 'Traffic Dodge Magnum RT',
				686736: 'Traffic Dodge Caliber',
				686914: 'Traffic Nissan Frontier',
				710030: 'Traffic Nissan Versa',
				745251: 'Pagani Zonda Cinque NFS Edition',
				745296: 'Pagani Zonda Cinque Roadster NFS Edition',
				1065045: 'Bentley Continental Supersports Convertible',
				1065090: 'Porsche 911 GT2 RS',
				1065135: 'Porsche 911 GT2 RS',
				1065149: 'Bugatti Veyron 16.4 Super Sport',
				1065194: 'Bugatti Veyron 16.4 Super Sport',
				1065267: 'Gumpert apollo s',
				1065312: 'Gumpert apollo s',
				1065326: 'Dodge Viper SRT10 Roadster Final Edition',
				1065371: 'Lamborghini Murciélago LP 650-4 Roadster',
				1111099: 'Lamborghini Countach 5000 quattrovalvole',
				1111150: 'Lamborghini Sesto Elemento',
				1111287: 'Lamborghini Diablo SV',
				1111341: 'Porsche 959',
				1111395: 'Porsche 911 Turbo',
				1111494: 'Porsche 911 Speedster',
				1111597: 'Lamborghini Sesto Elemento',
				1111604: 'Lamborghini Countach 5000 quattrovalvole',
				1111611: 'Lamborghini Diablo SV',
				1111618: 'Porsche 959',
				1111632: 'Porsche 911 Turbo',
				1111785: 'Porsche 911 Speedster'}

	if Id in Vehicles:
		return Vehicles[Id]

	return Id


def get_vehicle_flag(Flag):
	VehicleFlags = {0x1:  'E_VEHICLE_FLAG_COP',
				    0x2:  'E_VEHICLE_FLAG_SELECTABLE',
				    0x4:  'E_VEHICLE_FLAG_CONVERTIBLE',
				    0x8:  'E_VEHICLE_FLAG_TRAFFIC',
				    0x10: 'E_VEHICLE_FLAG_SELECTABLE_ONLINE'}

	if Flag in VehicleFlags:
		return VehicleFlags[Flag]

	return Flag


def get_drivetrain_type(Id):
	Drivetrain = {299037: 'All-Wheel',
				  299038: 'Front-Wheel',
				  299039: 'Rear-Wheel'}

	if Id in Drivetrain:
		return Drivetrain[Id]

	return Id


def get_engine_type(Type):
	EngineTypes = {299048: 'FLAT-4',
				   299049: 'FLAT-6',
				   299050: 'INLINE-4',
				   299051: 'V6',
				   299052: 'V8',
				   299053: 'V10',
				   299054: 'V12',
				   299055: 'W16',
				   383861: 'INLINE-5',
				   383863: 'W12'}

	if Type in EngineTypes:
		return EngineTypes[Type]

	return Type


def get_DLC_type(Id):
	DLCs = {1089001: 'Base game',
			1089002: 'Super Sports',
			1091295: 'Porsche Unleashed',
			1091296: 'Lamborghini Untamed',
			1097039: 'Limited Edition',
			1097040: 'SCPD Rebels/EA Crew Edition',
			1097041: 'Dr. Pepper',
			1097042: 'Online Pass'}

	if Id in DLCs:
		return DLCs[Id]

	return Id


def get_tier_type(Type):
	Tiers = {1: 'Sports/Traffic Police',
			 2: 'Performance/Highway Patrol',
			 3: 'Super/Rapid Deployment',
			 4: 'Exotic/Speed Enforcement',
			 5: 'Hyper/Special Response'}

	if Type in Tiers:
		return Tiers[Type]

	return Type


def get_country_type(Id):
	Country = {299006: 'United Kingdom',
			   299007: 'France',
			   299008: 'Germany',
			   299009: 'United States',
			   299010: 'Italy',
			   299011: 'Japan',
			   299012: 'Sweden'}

	if Id in Country:
		return Country[Id]

	return Id


def get_trigger_type(Type):
	TriggerTypes = {0xFF: 'E_TRIGGER_INVALID',
					0x06: 'E_TRIGGER_BODY_SHOP',
					0x07: 'E_TRIGGER_SECURITY_GATE_INDIVIDUAL',
					0x0B: 'E_TRIGGER_WARP',
					0x17: 'E_TRIGGER_COOLDOWN_SPOT',
					0x18: 'E_TRIGGER_ROAD_RULE',
					0x19: 'E_TRIGGER_KILL_TRAFFIC_SOURCE',
					0x1A: 'E_TRIGGER_KILL_TRAFFIC_TARGET',
					0x1B: 'E_TRIGGER_KILL_SPAWN_ROLLING_ROADBLOCK_SOURCE',
					0x1C: 'E_TRIGGER_KILL_SPAWN_ROLLING_ROADBLOCK_TARGET',
					0x1D: 'E_TRIGGER_AVOIDABLE_OBJECT',
					0x2F: 'E_TRIGGER_PARKED_COP_PLACEMENT',
					0x30: 'E_TRIGGER_SECURITY_GATE',
					0x31: 'E_TRIGGER_PURSUIT_BREAKER_JUMP_NO_ICON',
					0x32: 'E_TRIGGER_BILLBOARD',
					0x33: 'E_TRIGGER_DATA_POST',
					0x34: 'E_TRIGGER_SPEED_CAMERA',
					0x35: 'E_TRIGGER_BLACKSPOT_CAMERA_TRIGGER',
					0x36: 'E_TRIGGER_BLACKSPOT_CAMERA_LOCATION',
					0x37: 'E_TRIGGER_PURSUIT_BREAKER_JUMP',
					0x38: 'E_TRIGGER_PURSUIT_BREAKER_BLACKSPOT',
					0x39: 'E_TRIGGER_PURSUIT_BREAKER_STACK',
					0x3B: 'E_TRIGGER_PURSUIT_BREAKER_DROP_OFF',
					0x3C: 'E_TRIGGER_CAR_SWAP',
					0x3D: 'E_TRIGGER_CAR_PLACEMENT',
					0x3E: 'E_TRIGGER_WAITING_COP_PLACEMENT'}

	if Type in TriggerTypes:
		return TriggerTypes[Type]

	return Type


def get_trigger_shape(Shape):
	TriggerShapes = {0xFF: 'E_TRIGGERSHAPE_INVALID',
					 0x0: 'E_TRIGGERSHAPE_BOX',
					 0x1: 'E_TRIGGERSHAPE_SPHERE',
					 0x2: 'E_TRIGGERSHAPE_LOCATOR',
					 0x3: 'E_TRIGGERSHAPE_COUNT'}

	if Shape in TriggerShapes:
		return TriggerShapes[Shape]

	return Shape


def get_neighbour_flags(Flag):
	NeighbourFlags = {0x0: 'E_RENDERFLAG_NONE',
					  0x1: 'E_NEIGHBOURFLAG_RENDER',
					  0x2: 'E_NEIGHBOURFLAG_UNKNOWN_2',
					  0x3: 'E_NEIGHBOURFLAG_IMMEDIATE'}

	if Flag in NeighbourFlags:
		return NeighbourFlags[Flag]

	return Flag


def calculate_padding(lenght, alignment):
	division1 = (lenght/alignment)
	division2 = math.ceil(lenght/alignment)
	padding = int((division2 - division1)*alignment)
	return padding


def bytes_to_id(id):
	id = binascii.hexlify(id)
	id = str(id,'ascii')
	id = id.upper()
	id = '_'.join([id[x : x+2] for x in range(0, len(id), 2)])
	return id


def int_to_id(id):
	id = str(hex(int(id)))[2:].upper().zfill(8)
	id = '_'.join([id[::-1][x : x+2][::-1] for x in range(0, len(id), 2)])
	return id


def id_to_int(id):
	id_old = id
	id = id.replace('_', '')
	id = id.replace(' ', '')
	id = id.replace('-', '')
	id = ''.join(id[::-1][x:x+2][::-1] for x in range(0, len(id), 2))
	return int(id, 16)


def decode_resource_id(mResourceId, resource_type): # OK
	mResource = mResourceId
	if resource_type == "GraphicsSpec":
		mResource = id_to_int(mResourceId)

	elif resource_type == "CharacterSpec":
		mResource = id_to_int(mResourceId)

	elif resource_type == "InstanceList":
		for i in range(0, 1000):
			string = "TRK_UNIT%d_LIST" % i
			ID = hex(zlib.crc32(string.lower().encode()) & 0xffffffff)
			ID = ID[2:].upper().zfill(8)
			ID = '_'.join([ID[::-1][x:x+2][::-1] for x in range(0, len(ID), 2)]).lower()
			IDswap = swap_resource_id(ID)
			if (ID == mResourceId.lower()) or (IDswap == mResourceId.lower()):
				mResource = "TRK_UNIT%03d" % i
				break

	elif resource_type == "PolygonSoupList":
		for i in range(0, 1000):
			string = "TRK_COL_%d" % i
			ID = hex(zlib.crc32(string.lower().encode()) & 0xffffffff)
			ID = ID[2:].upper().zfill(8)
			ID = '_'.join([ID[::-1][x:x+2][::-1] for x in range(0, len(ID), 2)]).lower()
			IDswap = swap_resource_id(ID)
			if (ID == mResourceId.lower()) or (IDswap == mResourceId.lower()):
				mResource = "TRK_COL_%03d" % i
				break

	if mResource == mResourceId:
		print("WARNING: could not decode the Id of the resource %s of type %s." %(mResourceId, resource_type))

	return mResource


def nvidiaGet():
	spaths = bpy.utils.script_paths()
	for rpath in spaths:
		tpath = rpath + '\\addons\\nvidia-texture-tools-2.1.2-win\\bin64\\nvcompress.exe'
		if os.path.exists(tpath):
			npath = '"' + tpath + '"'
			return npath
		tpath = rpath + '\\addons\\nvidia-texture-tools-2.1.1-win64\\bin64\\nvcompress.exe'
		if os.path.exists(tpath):
			npath = '"' + tpath + '"'
			return npath
	return None


def calculate_resourceid(resource_name):
	ID = hex(zlib.crc32(resource_name.lower().encode()) & 0xffffffff)
	ID = ID[2:].upper().zfill(8)
	ID = '_'.join([ID[::-1][x:x+2][::-1] for x in range(0, len(ID), 2)])
	return ID


def swap_resource_id(mResourceId):
	mResourceId = mResourceId.replace('_', '')
	mResourceId = mResourceId[::-1]
	mResourceId = '_'.join([mResourceId[x:x+2][::-1] for x in range(0, len(mResourceId), 2)])
	return mResourceId


def option_to_resource_version(resource_version):
	if resource_version == 'OPT_A':
		return "NFSHPR_PC"
	elif resource_version == 'OPT_B':
		return "NFSHP_PC"
	elif resource_version == 'OPT_C':
		return "NFSHP_PS3"
	elif resource_version == 'OPT_D':
		return "NFSHP_X360"
	return "None"


def option_to_resource_type(resource_type):
	if resource_type == 'OPT_A':
		return "InstanceList"
	elif resource_type == 'OPT_B':
		return "GraphicsSpec"
	elif resource_type == 'OPT_C':
		return "CharacterSpec"
	elif resource_type == 'OPT_D':
		return "Model"
	elif resource_type == 'OPT_E':
		return "TriggerData"
	elif resource_type == 'OPT_F':
		return "ZoneList"
	elif resource_type == 'OPT_G':
		return "PolygonSoupList"
	elif resource_type == 'OPT_H':
		return "VehicleList"
	return "None"


def clearScene(context): # OK
	#for obj in bpy.context.scene.objects:
	#	obj.select_set(True)
	#bpy.ops.object.delete()

	for block in bpy.data.objects:
		#if block.users == 0:
		bpy.data.objects.remove(block, do_unlink = True)

	for block in bpy.data.meshes:
		if block.users == 0:
			bpy.data.meshes.remove(block)

	for block in bpy.data.materials:
		if block.users == 0:
			bpy.data.materials.remove(block)

	for block in bpy.data.textures:
		if block.users == 0:
			bpy.data.textures.remove(block)

	for block in bpy.data.images:
		if block.users == 0:
			bpy.data.images.remove(block)

	for block in bpy.data.cameras:
		if block.users == 0:
			bpy.data.cameras.remove(block)

	for block in bpy.data.lights:
		if block.users == 0:
			bpy.data.lights.remove(block)

	for block in bpy.data.armatures:
		if block.users == 0:
			bpy.data.armatures.remove(block)

	for block in bpy.data.collections:
		if block.users == 0:
			bpy.data.collections.remove(block)
		else:
			bpy.data.collections.remove(block, do_unlink=True)


def NFSHPLibraryGet(): # OK
	spaths = bpy.utils.script_paths()
	for rpath in spaths:
		tpath = rpath + '\\addons\\NeedForSpeedHotPursuit'
		if os.path.exists(tpath):
			npath = '"' + tpath + '"'
			return tpath
	return None


class Suppressor(object):

	def __enter__(self):
		self.stdout = sys.stdout
		sys.stdout = self

	def __exit__(self, type, value, traceback):
		sys.stdout = self.stdout
		if type is not None:
			raise

	def flush(self):
		pass

	def write(self, x):
		pass


@orientation_helper(axis_forward='-Y', axis_up='Z')
class ImportNFSHP(Operator, ImportHelper):
	"""Load a Need for Speed Hot Pursuit (2010/2020) model file"""
	bl_idname = "import_nfshp.data"  # important since its how bpy.ops.import_test.some_data is constructed
	bl_label = "Import models"
	bl_options = {'PRESET'}

	# ImportHelper mixin class uses this
	filename_ext = ".dat"

	filter_glob: StringProperty(
			options={'HIDDEN'},
			default="*.dat;*.BIN;*.BNDL",
			maxlen=255,  # Max internal buffer length, longer would be clamped.
			)

	# List of operator properties, the attributes will be assigned
	# to the class instance from the operator settings before calling.

	resource_version: EnumProperty(
			name="Resource version",
			description="Choose the resource version you want to load",
			items=(('OPT_A', "PC - NFSHPR", "Need for Speed Hot Pursuit Remastered (2020) for PC"),
				   ('OPT_B', "PC - NFSHP", "NOT SUPPORTED YET. Need for Speed Hot Pursuit for PC"),
				   ('OPT_C', "PS3 - NFSHP", "NOT SUPPORTED YET. Need for Speed Most Wanted 2012 for PS3"),
				   ('OPT_D', "X360 - NFSHP", "NOT SUPPORTED YET. Need for Speed Most Wanted 2012 for X360")),
			default='OPT_A',
			)

	resource_type: EnumProperty(
			name="Resource type",
			description="Choose the resource type you want to load",
			items=(('OPT_A', "InstanceList", "Track units"),
				   ('OPT_B', "GraphicsSpec", "Vehicles"),
				   ('OPT_C', "CharacterSpec", "Characters"),
				   ('OPT_D', "Model", "Standalone model"),
				   ('OPT_E', "TriggerData", "Triggers"),
				   ('OPT_F', "ZoneList", "PVS"),
				   ('OPT_G', "PolygonSoupList", "Collision")),
			default='OPT_B',
			)

	is_bundle: BoolProperty(
			name="Is bundle",
			description="Check if the importing file is a bundle",
			default=True,
			)

	clear_scene: BoolProperty(
			name="Clear scene",
			description="Check in order to clear the scene",
			default=True,
			)

	hide_low_lods: BoolProperty(
			name="Hide low LODs",
			description="Check in order to hide the models with low level of detail and keep only the most detailed ones",
			default=True,
			)

	hide_polygonsoup: BoolProperty(
			name="Hide collision objects",
			description="Check in order to hide the collision objects (PolygonSoup)",
			default=True,
			)

	hide_skeleton: BoolProperty(
			name="Hide skeleton",
			description="Check in order to hide the skeleton",
			default=True,
			)

	hide_controlmesh: BoolProperty(
			name="Hide control mesh",
			description="Check in order to hide the control mesh",
			default=True,
			)

	hide_effects: BoolProperty(
			name="Hide effect objects",
			description="Check in order to hide lights and other effects objects on vehicles",
			default=True,
			)

	random_color: BoolProperty(
			name="Apply randomized color",
			description="Check in order to apply randomized color on imported vehicle instead of the default white color",
			default=True,
			)

	if bpy.context.preferences.view.show_developer_ui == True:
		debug_prefer_shared_asset = False
		#debug_prefer_shared_asset: BoolProperty(
		#	name="Favor shared assets",
		#	description="Check in order to favor shared assets rather than bundle internal ones. Only for BPX360 rasters",
		#	default=False,
		#	)
	else:
		debug_prefer_shared_asset = False

	def execute(self, context): # OK
		if os.path.isfile(self.filepath) == False:
			self.report({"ERROR"}, "You must select a file to import.")
			return {"CANCELLED"}
		if NFSHPLibraryGet() == None:
			self.report({"ERROR"}, "Game library not found, please check if you installed it correctly.")
			return {"CANCELLED"}

		global_matrix = axis_conversion(from_forward='Z', from_up='Y', to_forward=self.axis_forward, to_up=self.axis_up).to_4x4()

		status = main(context, self.filepath, option_to_resource_version(self.resource_version), option_to_resource_type(self.resource_type), self.is_bundle,
					  self.clear_scene, self.debug_prefer_shared_asset, self.hide_low_lods, self.hide_polygonsoup, self.hide_skeleton, self.hide_controlmesh,
					  self.hide_effects, self.random_color, global_matrix)

		if status == {"CANCELLED"}:
			self.report({"ERROR"}, "Importing has been cancelled. Check the system console for information.")

		return status

	def draw(self, context):
		layout = self.layout
		layout.use_property_split = True
		layout.use_property_decorate = False  # No animation.

		sfile = context.space_data
		operator = sfile.active_operator

		##
		box = layout.box()
		split = box.split(factor=0.75)
		col = split.column(align=True)
		col.label(text="Settings", icon="SETTINGS")

		box.prop(operator, "resource_version")
		box.prop(operator, "resource_type")
		box.prop(operator, "is_bundle")
		if operator.resource_type == 'OPT_D':
			operator.is_bundle = False

		##
		box = layout.box()
		split = box.split(factor=0.75)
		col = split.column(align=True)
		col.label(text="Preferences", icon="OPTIONS")

		box.prop(operator, "clear_scene")
		box.prop(operator, "hide_low_lods")
		box.prop(operator, "hide_polygonsoup")
		box.prop(operator, "hide_skeleton")
		box.prop(operator, "hide_controlmesh")
		box.prop(operator, "hide_effects")
		box.prop(operator, "random_color")

		##
		box = layout.box()
		split = box.split(factor=0.75)
		col = split.column(align=True)
		col.label(text="Blender orientation", icon="OBJECT_DATA")

		row = box.row(align=True)
		row.label(text="Forward axis")
		row.use_property_split = False
		row.prop_enum(operator, "axis_forward", 'X', text='X')
		row.prop_enum(operator, "axis_forward", 'Y', text='Y')
		row.prop_enum(operator, "axis_forward", 'Z', text='Z')
		row.prop_enum(operator, "axis_forward", '-X', text='-X')
		row.prop_enum(operator, "axis_forward", '-Y', text='-Y')
		row.prop_enum(operator, "axis_forward", '-Z', text='-Z')

		row = box.row(align=True)
		row.label(text="Up axis")
		row.use_property_split = False
		row.prop_enum(operator, "axis_up", 'X', text='X')
		row.prop_enum(operator, "axis_up", 'Y', text='Y')
		row.prop_enum(operator, "axis_up", 'Z', text='Z')
		row.prop_enum(operator, "axis_up", '-X', text='-X')
		row.prop_enum(operator, "axis_up", '-Y', text='-Y')
		row.prop_enum(operator, "axis_up", '-Z', text='-Z')


def menu_func_import(self, context): # OK
	pcoll = preview_collections["main"]
	my_icon = pcoll["my_icon"]
	self.layout.operator(ImportNFSHP.bl_idname, text="Need for Speed Hot Pursuit (2010/2020) (.BIN, .BNDL, .dat)", icon_value=my_icon.icon_id)


classes = (
		ImportNFSHP,
)

preview_collections = {}


def register(): # OK
	import bpy.utils.previews
	pcoll = bpy.utils.previews.new()

	my_icons_dir = os.path.join(os.path.dirname(__file__), "dgi_icons")
	pcoll.load("my_icon", os.path.join(my_icons_dir, "nfshp_icon.png"), 'IMAGE')

	preview_collections["main"] = pcoll

	for cls in classes:
		bpy.utils.register_class(cls)
	bpy.types.TOPBAR_MT_file_import.append(menu_func_import)


def unregister(): # OK
	for pcoll in preview_collections.values():
		bpy.utils.previews.remove(pcoll)
	preview_collections.clear()

	for cls in classes:
		bpy.utils.unregister_class(cls)
	bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)


if __name__ == "__main__":
	register()
