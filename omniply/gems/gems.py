from .abstract import AbstractGem
from .imports import *
from omnibelt import unspecified_argument
from omnibelt.crafts import InheritableCrafty, AbstractCraft, NestableCraft



class GemBase(NestableCraft, AbstractGem):
	_no_value = object()
	def __init__(self, default: Optional[Any] = _no_value, *, final: bool = None, **kwargs):
		super().__init__(**kwargs)
		self._name = None
		self._owner = None
		self._default = default
		self._final = final
		self._content = []
		self._fn = None


	def _wrapped_content(self): # wrapped method
		return self._fn


	def __call__(self, fn: Optional[Union['GemBase', Callable]] = None, **content: str):
		if fn is not None:
			assert self._fn is None, 'GemBase already has a function'
			self._fn = fn
		else:
			self._content.append(content)
		return self


	def __set_name__(self, owner, name):
		self._name = name
		self._owner = owner


	def __get__(self, instance, owner):
		return self.resolve(instance)


	def __set__(self, instance, value):
		raise NotImplementedError


	def __delete__(self, instance):
		raise NotImplementedError



class CachableGem(GemBase):
	def __init__(self, default: Optional[Any] = GemBase._no_value, *, cache: bool = True, **kwargs):
		super().__init__(default=default, **kwargs)
		self._cache = cache


	def resolve(self, instance: InheritableCrafty):
		if not self._cache:
			return self.realize(instance)

		val = instance.__dict__.get(self._name, self._no_value)
		if val is self._no_value:
			val = self.realize(instance)
			instance.__dict__[self._name] = val
		return val


	def realize(self, instance: InheritableCrafty):
		if self._default is self._no_value:
			return self._fn(instance)
		return self._default



class FinalizedGem(GemBase):
	def __init__(self, default: Optional[Any] = GemBase._no_value, *, final: bool = True, **kwargs):
		super().__init__(default=default, **kwargs)
		self._final = final

	def __set__(self, instance, value):
		if self._final:
			raise AttributeError(f'cannot set `final` gem {self._name}')
		super().__set__(instance, value)



class InheritableGem(GemBase):
	def __init__(self, default: Optional[Any] = GemBase._no_value, *, inherit: bool = True, **kwargs):
		super().__init__(default=default, **kwargs)
		self._inherit = inherit

	@property
	def inherit(self):
		return self._inherit

