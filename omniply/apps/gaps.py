from typing import Iterable, Self, Mapping, Any, Iterator
from collections import UserDict

from .. import AbstractGadget, AbstractGaggle
from ..core.gaggles import CraftyGaggle, MutableGaggle
from ..core.games import CacheGame
from ..core.tools import ToolCraft, AutoToolCraft
from ..core.genetics import AutoMIMOFunctionGadget
from .. import ToolKit as _ToolKit, tool as _tool, Context as _Context



GAUGE = dict[str, str]


class AbstractGauged(AbstractGadget):
	def gauge_apply(self, gauge: GAUGE) -> Self:
		raise NotImplementedError



class AbstractGapped(AbstractGauged):
	def gap(self, internal_gizmo: str) -> str:
		'''Converts an internal gizmo to its external representation.'''
		raise NotImplementedError



class Gauged(AbstractGauged):
	def __init__(self, *, gauge: Mapping[str, str] = None, **kwargs):
		if gauge is None:
			gauge = {}
		super().__init__(**kwargs)
		self._gauge = gauge


	def gauge_apply(self, gauge: GAUGE) -> Self:
		'''Applies the gauge to the Gauged.'''
		self._gauge.update(gauge)
		return self



class Gapped(Gauged, AbstractGapped):
	def gap(self, internal_gizmo: str) -> str:
		'''Converts an internal gizmo to its external representation.'''
		return self._gauge.get(internal_gizmo, internal_gizmo)



class GaugedGaggle(MutableGaggle, Gauged):
	def extend(self, gadgets: Iterable[AbstractGauged]) -> Self:
		'''Extends the Gauged with the provided gadgets.'''
		gadgets = list(gadgets)
		for gadget in gadgets:
			# if isinstance(gadget, AbstractGauged):
			gadget.gauge_apply(self._gauge)
		return super().extend(gadgets)


	def gauge_apply(self, gauge: GAUGE) -> Self:
		'''Applies the gauge to the GaugedGaggle.'''
		super().gauge_apply(gauge)
		for gadget in self.vendors():
			if isinstance(gadget, AbstractGauged):
				gadget.gauge_apply(gauge)
		table = {gauge.get(gizmo, gizmo): gadgets for gizmo, gadgets in self._gadgets_table.items()}
		self._gadgets_table.clear()
		self._gadgets_table.update(table)
		return self


class GaugedGame(CacheGame, GaugedGaggle):
	def gauge_apply(self, gauge: GAUGE) -> Self:
		super().gauge_apply(gauge)
		cached = {key: value for key, value in self.data.items() if key in gauge}
		for key, value in cached.items():
			del self.data[key]
		self.data.update({gauge[key]: value for key, value in cached.items()})
		return self


class AutoFunctionGapped(AutoMIMOFunctionGadget, AbstractGapped):
	def gap(self, internal_gizmo: str) -> str:
		'''Converts an internal gizmo to its external representation.'''
		return self._arg_map.get(internal_gizmo, internal_gizmo)


	def gauge_apply(self, gauge: GAUGE) -> Self:
		'''Applies the gauge to the Gauged.'''
		self._arg_map.update(gauge)
		return self

	def gizmos(self) -> Iterator[str]:
		for gizmo in super().gizmos():
			yield self.gap(gizmo)




class GappedTool(ToolCraft):
	class _ToolSkill(Gapped, ToolCraft._ToolSkill):
		def gizmos(self) -> Iterable[str]:
			'''Lists the gizmos produced by the tool.'''
			for gizmo in super().gizmos():
				yield self.gap(gizmo)



class GappedAutoTool(AutoFunctionGapped, AutoToolCraft):
	class _ToolSkill(AutoFunctionGapped, AutoToolCraft._ToolSkill):
		pass



class ToolKit(_ToolKit, Gapped, GaugedGaggle):
	pass



class Context(_Context, GaugedGame):
	pass



class tool(_tool):
	_ToolCraft = GappedAutoTool
	class from_context(_tool.from_context):
		_ToolCraft = GappedTool



def test_gauge():

	class Kit1(ToolKit):
		@tool('a')
		def f(self, x, y):
			return x + y

	@tool('b')
	def g(x, y):
		return x - y

	kit = Kit1()

	assert list(kit.gizmos()) == ['a']

	kit.gauge_apply({'a': 'z'})

	assert list(kit.gizmos()) == ['z']

	ctx = Context(kit, g)

	assert list(ctx.gizmos()) == ['z', 'b']

	ctx.gauge_apply({'b': 'w'})

	assert list(ctx.gizmos()) == ['z', 'w']
	assert list(g.gizmos()) == ['w']

	ctx['x'] = 1
	ctx['y'] = 2

	ctx.gauge_apply({'x': 'c'})

	assert ctx['c'] == 1
	assert ctx['w'] == -1
	assert ctx['z'] == 3

	assert ctx.grab('a', None) is None
	assert ctx.grab('b', None) is None


def test_gapped_tools():

	class Kit(ToolKit):
		@tool.from_context('x', 'y')
		def f(self, game):
			return game[self.gap('a')], game[self.gap('b')] + game[self.gap('c')]
		@f.parents
		def _f_parents(self):
			return map(self.gap, ['a', 'b', 'c'])


	kit = Kit(gauge={'a': 'z'})

	assert list(kit.gizmos()) == ['x', 'y']

	ctx = Context(kit)

	ctx.update({'z': 1, 'b': 2, 'c': 3})

	assert ctx['x'] == 1 and ctx['y'] == 5

	gene = next(kit.genes('x'))

	assert gene.parents == ('z', 'b', 'c')










