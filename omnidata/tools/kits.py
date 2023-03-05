from typing import Tuple, List, Dict, Optional, Union, Any, Callable, Sequence, Iterator, Iterable, Type, Set

from omnibelt import method_decorator, agnostic, unspecified_argument
from omnibelt.crafts import AbstractCraft, AbstractCrafty, NestableCraft, SkilledCraft, IndividualCrafty

from ..features import Prepared

from .abstract import AbstractSpaced, Loggable, AbstractAssessible, AbstractKit, SingleVendor, AbstractTool
from .errors import ToolFailedError, MissingGizmoError
from .crafts import ToolCraft, OptionalCraft, DefaultCraft, LabelCraft, SpaceCraft, InitCraft, ReplaceableCraft
from .assessments import AbstractSignature, Signatured



class CraftyKit(IndividualCrafty, AbstractSpaced, AbstractKit):
	class _SkillTool(AbstractTool): # collects all skills (of the whole mro) of one gizmo
		def __init__(self, label: str, **kwargs):
			super().__init__(**kwargs)
			self._label = label
			self._standard = []
			self._optionals = []
			self._defaults = []


		def add(self, skill: ToolCraft.Skill):
			if isinstance(skill, OptionalCraft.Skill):
				self._optionals.append(skill)
			elif isinstance(skill, DefaultCraft.Skill):
				self._defaults.append(skill)
			else:
				self._standard.append(skill)


		def tool_history(self):
			yield from self._standard
			yield from self._optionals
			yield from self._defaults


		def tool(self):
			return next(self.tool_history())


		def tools(self): # by default, only uses the newest tool in the class hierarchy
			yield self.tool()


	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self._tools = {}
		self._spaces = {}


	def _process_skill(self, src: Type[AbstractCrafty], key: str, craft: AbstractCraft, skill: LabelCraft.Skill):
		super()._process_skill(src, key, craft, skill)
		if isinstance(skill, ToolCraft.Skill):
			if skill.label not in self._tools:
				self._tools[skill.label] = self._SkillTool(skill.label)
			self._tools[skill.label].add(skill)
		if isinstance(skill, SpaceCraft.Skill):
			self._spaces.setdefault(skill.label, []).append(skill)


	def has_gizmo(self, gizmo: str) -> bool:
		return gizmo in self._tools


	def space_of(self, gizmo: str):
		if gizmo in self._spaces:
			return self._spaces[gizmo][0].space_of(gizmo)
		return self._tools[gizmo].space_of(gizmo)


	def vendors(self, gizmo: str):
		# gizmo = self.validate_label(gizmo)
		if gizmo not in self._tools:
			raise MissingGizmoError(gizmo)
		yield from self._tools[gizmo].tools()


	def tools(self) -> Iterator['AbstractTool']:
		for skill in self._tools.values():
			yield from skill.tools()



class ValidatedKit(CraftyKit):
	@classmethod
	def validate_label(cls, label):
		return label



class RelabeledKit(CraftyKit):
	_inherited_tool_relabels = None
	def __init_subclass__(cls, replace=None, **kwargs): # {old_label: new_label}
		if replace is None:
			replace = {}
		super().__init_subclass__(**kwargs)
		past = {}
		for parent in cls.__bases__:
			if issubclass(parent, RelabeledKit) and parent._inherited_tool_relabels is not None:
				past.update(parent._inherited_tool_relabels)
		replace.update(past)
		cls._inherited_tool_relabels = replace


	@classmethod
	def _emit_all_craft_items(cls, *, remaining: Iterator[Type['InheritableCrafty']] = None,
	                          start : Type['InheritableCrafty'] = None,
	                          **kwargs) -> Iterator[Tuple[Type[AbstractCrafty], str, AbstractCraft]]: # N-O
		if start is None:
			start = cls

		for loc, key, craft in super()._emit_all_craft_items(remaining=remaining, start=start, **kwargs):
			if loc is start:
				yield loc, key, craft
			elif len(start._inherited_tool_relabels) and isinstance(craft, ReplaceableCraft):
				fix = craft.replace(start._inherited_tool_relabels)
				yield loc, key, fix
			else:
				yield loc, key, craft



class MaterialedCrafty(CraftyKit, Prepared): # allows materials to be initialized when prepared
	def _prepare(self, *args, **kwargs):
		super()._prepare(*args, **kwargs)

		materials = {}
		for gizmo, tool in self._tools.items():
			if isinstance(tool, self._SkillTool):
				skill = tool.tool()
				if isinstance(skill, InitCraft.Skill):
					materials[gizmo] = skill.init(self)
		self._tools.update(materials)



class SignaturedCrafty(CraftyKit, Signatured):
	@agnostic
	def signatures(self, owner = None) -> Iterator['AbstractSignature']:
		if isinstance(self, type):
			self: Type['SignaturedCrafty']
			for loc, key, craft in self._emit_all_craft_items():
				if isinstance(craft, Signatured):
					yield from craft.signatures(self)
		else:
			for tool in self.tools():
				if isinstance(tool, Signatured):
					yield from tool.signatures(self)



class AssessibleCrafty(CraftyKit, AbstractAssessible):
	@classmethod
	def assess_static(cls, assessment):
		super().assess_static(assessment)
		for owner, key, craft in cls._emit_all_craft_items():
			if isinstance(craft, AbstractAssessible):
				assessment.add_edge(cls, craft, name=key, loc=owner)
				assessment.expand(craft)


	def assess(self, assessment):
		super().assess(assessment)
		for tool in self.tools():
			if isinstance(tool, AbstractAssessible):
				assessment.add_edge(self, tool)
				assessment.expand(tool)
















