from typing import Tuple, List, Dict, Optional, Union, Any, Callable, Sequence, Iterator, Iterable, Hashable
from omnibelt import unspecified_argument

from .. import spaces

from .errors import ToolFailedError



class Gizmoed:
	def gizmos(self) -> Iterator[str]:
		raise NotImplementedError


	def has_gizmo(self, gizmo: str) -> bool:
		raise NotImplementedError



class Tooled(Gizmoed):
	def tools(self) -> Iterator['AbstractTool']:
		raise NotImplementedError


	def vendors(self, gizmo: str) -> Iterator['AbstractTool']:
		raise NotImplementedError


	def has_gizmo(self, gizmo: str) -> bool:
		return any(tool.has_gizmo(gizmo) for tool in self.tools())



class SingleVendor(Tooled):
	def vendor(self, gizmo: str, default: Any = unspecified_argument) -> 'AbstractTool':
		raise NotImplementedError


	def vendors(self, gizmo: str) -> Iterator['AbstractTool']:
		yield self.vendor(gizmo)



class AbstractTool(Gizmoed): # leaf/source
	def get_from(self, ctx: Optional['AbstractContext'], gizmo: str):
		raise NotImplementedError


	def __getitem__(self, gizmo: str):
		return self.get_from(None, gizmo)



class AbstractContext(AbstractTool):
	@property
	def context_id(self) -> Hashable:
		raise NotImplementedError


	def __hash__(self):
		return hash(self.context_id)


	def __eq__(self, other):
		if isinstance(other, AbstractContext):
			return self.context_id == other.context_id
		return NotImplemented


	def __getitem__(self, gizmo: str):
		return self.get_from(self, gizmo)



class AbstractKit(Tooled, AbstractTool): # branch/router
	def gizmos(self) -> Iterator[str]:
		past = set()
		for tool in self.tools():
			for gizmo in tool.gizmos():
				if gizmo not in past:
					past.add(gizmo)
					yield gizmo


	def vendors(self, gizmo: str):
		for tool in self.tools():
			if tool.has_gizmo(gizmo):
				yield tool


	def get_from(self, ctx: Optional['AbstractContext'], gizmo: str):
		tries = 0
		for vendor in self.vendors(gizmo):
			try:
				return vendor.get_from(ctx, gizmo)
			except ToolFailedError:
				tries += 1
		raise ToolFailedError(f'No vendor for {gizmo} in {self} (tried {tries} vendor/s)')



class AbstractSpaced(AbstractTool):
	def space_of(self, gizmo: str) -> spaces.Dim:
		raise NotImplementedError








