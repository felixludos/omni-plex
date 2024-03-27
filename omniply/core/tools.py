from typing import Iterator, Optional, Any, Iterable, Callable
from omnibelt.crafts import AbstractSkill, AbstractCraft, AbstractCrafty, NestableCraft

from .abstract import AbstractGadget, AbstractGaggle, AbstractGig
from .gadgets import GadgetBase, FunctionGadget
from .genetics import AutoMIMOFunctionGadget


class SkillBase(AbstractSkill):
	def __init__(self, *, unbound_fn: Callable, base: Optional[AbstractCraft] = None, **kwargs):
		super().__init__(**kwargs)
		self._unbound_fn = unbound_fn
		self._base = base


	def __get__(self, instance, owner):
		if instance is None:
			return self
		return self._unbound_fn.__get__(instance, owner)


class CraftBase(NestableCraft):
	@property
	def __call__(self):
		"""
		Calling a ToolCraft instance directly results in the wrapped function being called.

		Returns:
			Callable: The wrapped function.
		"""
		return self._wrapped_content_leaf()

	def __get__(self, instance, owner):
		"""
		When accessing ToolCraft instances directly, they behave as regular methods, applying __get__ to the wrapped function.

		Args:
			instance: The instance that the method is being accessed through, or None when the method is accessed through the owner.
			owner: The owner class.

		Returns:
			Callable: The wrapped function.
		"""
		return self._wrapped_content_leaf().__get__(instance, owner)

	def _wrapped_content(self):
		"""
		Returns the wrapped function. This may be a nested craft or other decorator.

		Note: If you want the actual function, use _wrapped_content_leaf.

		Returns:
			Callable: The wrapped function.
		"""
		return self._fn



# class ToolSkill(AbstractSkill):
# 	"""
# 	The ToolSkill class is a subclass of AbstractSkill. It provides methods to handle unbound functions and their bases.
#
# 	Attributes:
# 		_unbound_fn (Callable): The unbound function to be handled.
# 		_base (Optional[AbstractCraft]): The base of the unbound function. Defaults to None.
# 	"""
#
# 	def __init__(self, *, unbound_fn: Callable, base: Optional[AbstractCraft] = None, **kwargs):
# 		"""
# 		Initializes a new instance of the ToolSkill class.
#
# 		Args:
# 			unbound_fn (Callable): The unbound function to be handled.
# 			base (Optional[AbstractCraft]): The base of the unbound function. If not provided, base will be None.
# 			kwargs: Arbitrary keyword arguments.
# 		"""
# 		super().__init__(**kwargs)
# 		self._unbound_fn = unbound_fn
# 		self._base = base
#
# 	def __get__(self, instance, owner):
# 		"""
# 		Returns the unbound function if the instance is None, otherwise it returns the bound method.
#
# 		Args:
# 			instance: The instance that the method is being accessed through, or None when the method is accessed through the owner.
# 			owner: The owner class.
#
# 		Returns:
# 			Callable: The unbound function if the instance is None, otherwise the bound method.
# 		"""
# 		if instance is None:
# 			return self
# 		return self._unbound_fn.__get__(instance, owner)

class ToolCraft(FunctionGadget, CraftBase):
	"""
	The ToolCraft class is a subclass of FunctionGadget and NestableCraft. It provides methods to handle gizmos and their associated functions.

	Attributes:
		_ToolSkill (FunctionGadget, ToolSkill): A nested class that inherits from FunctionGadget and ToolSkill.
	"""

	class _ToolSkill(FunctionGadget, SkillBase):
		"""
		The _ToolSkill class is a nested class that inherits from FunctionGadget and ToolSkill.
		"""
		pass

	def as_skill(self, owner: AbstractCrafty) -> SkillBase:
		"""
		When an AbstractCrafty is instantiated (i.e., `owner`), any crafts accessible by the class (including inherited ones) can be converted to skills.

		Args:
			owner (AbstractCrafty): The owner of the craft.

		Returns:
			ToolSkill: The converted skill.
		"""
		unbound_fn = self._wrapped_content_leaf()
		fn = unbound_fn.__get__(owner, type(owner))
		return self._ToolSkill(fn=fn, gizmo=self._gizmo, unbound_fn=unbound_fn, base=self)


class AutoToolCraft(AutoMIMOFunctionGadget, ToolCraft):
	class _ToolSkill(AutoMIMOFunctionGadget, SkillBase):
		pass


class ToolDecorator(GadgetBase):
	"""
	The ToolDecorator class is a subclass of GadgetBase. It provides methods to handle gizmo decoration.

	Attributes:
		_gizmo_type (None): The type of the gizmo. Defaults to None.
		_gizmo (str): The gizmo to be handled.
		_ToolCraft (ToolCraft): A nested class that inherits from ToolCraft.
	"""

	_gizmo_type = None

	def __init__(self, gizmo: str, **kwargs):
		"""
		Initializes a new instance of the ToolDecorator class.

		Args:
			gizmo (str): The gizmo to be handled.
			kwargs: Arbitrary keyword arguments.
		"""
		if isinstance(gizmo, str) and self._gizmo_type is not None:
			gizmo = self._gizmo_type(gizmo)
		super().__init__(**kwargs)
		self._gizmo = gizmo

	def gizmos(self) -> Iterator[str]:
		"""
		Lists gizmos produced by self.

		Returns:
			Iterator[str]: An iterator over the gizmos.
		"""
		yield self._gizmo

	def gives(self, gizmo: str) -> bool:
		"""
		Checks if a gizmo is can be produced by this gadget.

		Args:
			gizmo (str): The name of the gizmo to check.

		Returns:
			bool: True if the gizmo can be grabbed, False otherwise.
		"""
		return gizmo == self._gizmo

	def grab_from(self, ctx: Optional[AbstractGig], gizmo: str) -> Any:
		"""
		Tries to grab a gizmo from the context.

		Args:
			ctx (Optional[AbstractGig]): The context from which to grab the gizmo.
			gizmo (str): The name of the gizmo to grab.

		Returns:
			Any: The grabbed gizmo.

		Raises:
			_GadgetFailed: If the gizmo cannot be grabbed.
		"""
		raise self._GadgetFailure(gizmo)

	_ToolCraft = ToolCraft

	def _actualize_tool(self, fn: Callable, **kwargs):
		"""
		Actualizes a tool by creating a ToolCraft instance with the gizmo and the function.

		Args:
			fn (Callable): The function to be actualized.
			kwargs: Arbitrary keyword arguments.

		Returns:
			ToolCraft: The actualized tool.
		"""
		return self._ToolCraft(gizmo=self._gizmo, fn=fn, **kwargs)

	def __call__(self, fn):
		"""
		Calling a ToolDecorator instance directly results in the actualization of the function.

		Args:
			fn (Callable): The function to be actualized.

		Returns:
			ToolCraft: The actualized tool.
		"""
		return self._actualize_tool(fn)

class AutoToolDecorator(ToolDecorator):
	"""
	The AutoToolDecorator class is a subclass of ToolDecorator. It overrides the _ToolCraft attribute of the parent class
	with AutoToolCraft. This means that when a tool is actualized, an instance of AutoToolCraft will be created instead
	of ToolCraft.

	Attributes:
		_ToolCraft (AutoToolCraft): A nested class that inherits from AutoToolCraft.
	"""
	_ToolCraft = AutoToolCraft


	def __init__(self, *gizmos: str, **kwargs):
		"""
		Important: a single gizmo is always interpretted as a MISO (not MIMO).

		To use a MIMO with a single output gizmo you must pass a 1-element tuple/list (why would you do that though?)

		"""
		gizmo = None
		if len(gizmos) == 1:
			if isinstance(gizmos[0], str):
				gizmo = gizmos[0]
				gizmos = None
			else:
				assert len(gizmos[0]) == 1, f'Cannot interpret {gizmos[0]} as a single gizmo'

		if gizmos is not None:
			gizmos = tuple(self._gizmo_type(gizmo) if isinstance(gizmo, str) and self._gizmo_type is not None
						   else gizmo for gizmo in gizmos)
		super().__init__(gizmo=gizmo, **kwargs)
		self._gizmos = gizmos

	def _actualize_tool(self, fn: Callable, **kwargs):
		return super()._actualize_tool(fn, gizmos=self._gizmos, **kwargs)









