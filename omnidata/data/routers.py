from typing import Tuple, List, Dict, Optional, Union, Any, Callable, Sequence, Iterator, Iterable

from collections import OrderedDict
from omnibelt import get_printer, unspecified_argument

from .. import util
from ..structure import Sampler, Generator
from .abstract import AbstractDataRouter, AbstractDataSource, AbstractBatchable
from .sources import SpacedSource


prt = get_printer(__file__)


class ExpectingDataRouter(AbstractDataRouter):
	def __init_subclass__(cls, materials=None, required_materials=None, **kwargs):
		super().__init_subclass__(**kwargs)
		if required_materials is not None:
			raise NotImplementedError
		if isinstance(materials, str):
			materials = [materials]
		base = getattr(cls, '_expecting_materials', [])
		cls._expecting_materials = base + (materials or [])


	def _prepare(self, source=None, **kwargs):
		super()._prepare(source=source, **kwargs)
		for material in self._expecting_materials:
			if not self.has(material):
				prt.warning(f'Expected material {material!r} not found in {self}')



class DataCollection(AbstractBatchable, AbstractDataRouter):
	def __init__(self, *, materials_table=None, **kwargs):
		if materials_table is None:
			materials_table = self._MaterialsTable()
		super().__init__(**kwargs)
		self._registered_materials = materials_table
	
	_MaterialsTable = OrderedDict
	
	def copy(self):
		new = super().copy()
		new._registered_materials = new._registered_materials.copy()
		return new
	
	
	def _get_from(self, source, key):
		return self.get_material(key).get_from(source, key)
	
	
	def named_materials(self) -> Iterator[Tuple[str, 'AbstractDataSource']]:
		for name in self._registered_materials:
			yield name, self.get_material(name)
	
	def get_material(self, name, default=unspecified_argument):
		if name in self._registered_materials:
			material = getattr(self, name, unspecified_argument)
			if material is not unspecified_argument:
				return material
			if isinstance(material, str):
				return self.get_material(material, default=default)
		if default is not unspecified_argument:
			return default
		raise self.MissingMaterial(name)
	
	def has(self, name):
		return name in self._registered_materials
	
	
	# def _fingerprint_data(self):
	# 	# data = super()._fingerprint_data()
	# 	# if self.is_ready:
	# 	# 	data['buffers'] = {}
	# 	# 	for name, buffer in self.iter_named_buffers():
	# 	# 		data['buffers'][name] = buffer.fingerprint()
	# 	# return data
	# 	# return {'buffers': {name:buffer.fingerprint() for name, buffer in self.iter_named_buffers()}, 'ready': self.is_ready,
	# 	#         **super()._fingerprint_data()}
	# 	raise NotImplementedError
	
	
	def remove_material(self, name):
		self._registered_materials.remove(name)
	
	def register_material(self, name, material):
		if not isinstance(material, AbstractDataSource):
			prt.warning(f'Expected material for {name} in {self}, got: {material!r}')
		self._registered_materials[name] = material
	
	def rename_material(self, current, new):
		material = self.get_material(current, None)
		if material is not None:
			self.remove_material(current)
		self.register_material(new, material)



class SampleCollection(DataCollection, Sampler):
	def batch(self, batch_size, gen=None, **kwargs):
		if gen is None:
			gen = self.gen
		return super().batch(batch_size, gen=gen, **kwargs)

	_sample_key = None
	def _sample(self, shape, gen, sample_key=unspecified_argument):
		if sample_key is unspecified_argument:
			sample_key = self._sample_key
		N = shape.numel()
		samples = batch[sample_key]
		return util.split_dim(samples, *shape)
		return self.sample_material(sample_key, N, gen=gen)

	def sample_material(self, sample, N, gen=None):
		batch = self.batch(N, gen=gen)

		if sample_key is None:
			raise NotImplementedError
			return batch

		pass



class Generative(SampleCollection):
	def generate(self, *shape, gen=None):
		return self.sample(*shape, gen=gen)



class BranchedDataRouter(DataCollection):
	def register_material(self, name, material=None, *, space=None, **kwargs): # TODO: with delimiter for name
		raise NotImplementedError
		if material is None:
			material = self._SimpleMaterial(space=space, **kwargs)
		elif not isinstance(material, AbstractDataSource):
			material = self._SimpleMaterial(material, space=space, **kwargs)
		return super().register_material(name, material)



class SimpleDataCollection(DataCollection):
	_SimpleMaterial = None
	
	def register_material(self, name, material=None, *, space=None, **kwargs):
		if material is None:
			material = self._SimpleMaterial(space=space, **kwargs)
		elif not isinstance(material, AbstractDataSource):
			material = self._SimpleMaterial(material, space=space, **kwargs)
		return super().register_material(name, material)



class AliasedDataCollection(DataCollection):
	def register_material_alias(self, name: str, *aliases: str):
		'''
		Registers aliases for a material.

		Args:
			name: original name of the material
			*aliases: all the new aliases

		Returns:

		'''
		for alias in aliases:
			self._registered_materials[alias] = name
	
	def has(self, name):
		alias = self._registered_materials[name]
		return super().has(name) and (not isinstance(alias, str) or self.has(alias))



# class CachedDataRouter(AbstractDataRouter):
# 	def cached(self) -> Iterator[str]:
# 		raise NotImplementedError
#
# 	def __str__(self):
# 		cached = set(self.cached())
# 		return f'{self._title()}(' \
# 		       f'{", ".join((key if key in cached else "{" + key + "}") for key in self.available())})'



# def __setattr__(self, key, value):
# 	if isinstance(value, AbstractCollection):
# 		self._register_multi_material(value, *value.available())
# 	if isinstance(value, AbstractMaterial):
# 		self.register_material(key, value)
# 	super().__setattr__(key, value)
#
# def __delattr__(self, name):
# 	if name in self._registered_materials:
# 		self.remove_material(name)
# 	super().__delattr__(name)













