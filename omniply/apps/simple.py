from typing import Any, Iterator, Callable, Optional
from collections import UserDict
from omnibelt import filter_duplicates

# from collections import frozenset

from ..core import AbstractGig
from ..core.gadgets import GadgetBase



class DictGadget(GadgetBase):
	def __init__(self, *srcs: dict, **data):
		super().__init__()
		self.data = {**data}
		self._srcs = srcs


	def __delitem__(self, key):
		raise NotImplementedError


	def __getitem__(self, item):
		if item in self.data:
			return self.data[item]
		for src in self._srcs:
			if item in src:
				return src[item]
		raise KeyError(f'Key not found: {item}')


	def gizmos(self) -> Iterator[str]:
		yield from filter_duplicates(self.data.keys(), *map(lambda x: x.keys(), self._srcs))


	def grab_from(self, ctx: 'AbstractGig', gizmo: str) -> Any:
		return self[gizmo]



class Table(GadgetBase):
	_index_gizmo = 'index'
	_index_attribute = None

	def __init__(self, data_in_columns: dict[str, list[Any]] = None, **kwargs):
		super().__init__(**kwargs)
		assert self._index_gizmo is None or self._index_attribute is None, \
			f'Cannot specify both index_gizmo and index_attribute'
		self._columns = None
		self.data = data_in_columns
		self._loaded_data = data_in_columns is not None


	@property
	def is_loaded(self):
		return self._loaded_data


	def load(self):
		if not self.is_loaded:
			self.data = self._load_data()
			self._columns = tuple(self.data)
			self._loaded_data = self.data is not None
		return self


	def _load_data(self) -> dict[str, list[Any]]:
		raise NotImplementedError


	@property
	def columns(self) -> list[str]:
		if self._columns is None:
			self.load()
		return self._columns


	@property
	def number_of_rows(self) -> int:
		return len(self.data[self.columns[0]])


	def grab_from(self, ctx: 'AbstractGig', gizmo: str) -> Any:
		self.load()
		index = ctx.grab(self._index_gizmo) if self._index_attribute is None else getattr(ctx, self._index_attribute)
		return self.data[gizmo][index]


	def gizmos(self) -> Iterator[str]:
		yield from self.columns


	def __len__(self):
		return self.number_of_rows


	def __getitem__(self, index: int):
		self.load()
		return {col: self.data[col][index] for col in self.columns}


	@staticmethod
	def _validate_rows(rows: list[dict[str, Any]]) -> dict[str, list[Any]]:
		assert len(rows), f'Cannot create table from empty rows'
		cols = frozenset(col for row in rows for col in row)
		assert all(frozenset(row) == cols for row in rows), f'Inconsistent columns'
		return {col: [row[col] for row in rows] for col in rows[0]}


	@staticmethod
	def _validate_columns(columns: dict[str, list[Any]]) -> dict[str, list[Any]]:
		assert len(columns), f'Cannot create table from empty columns'
		lens = [len(col) for col in columns.values()]
		assert all(lens[0] == l for l in lens), f'Inconsistent column lengths'
		return columns.copy()

















