
from typing import List, Dict, Tuple, Optional, Union, Any, Hashable, Sequence, Callable, Generator, Type, Iterable, \
	Iterator, NamedTuple, ContextManager
import inspect
from omnibelt import split_dict, unspecified_argument, agnosticmethod, OrderedSet, \
	extract_function_signature, method_wrapper, agnostic, Modifiable

from ..persistent import AbstractFingerprinted, Fingerprinted

from .abstract import AbstractParameterized, AbstractHyperparameter



class ParameterizedBase(AbstractParameterized):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **self._extract_hparams(kwargs))


	class _find_missing_hparam:
		def __init__(self, base, **kwargs):
			super().__init__(**kwargs)
			self.base = base


		def __call__(self, name, default=inspect.Parameter.empty):
			value = getattr(self.base, name, default)
			if value is inspect.Parameter.empty:
				raise KeyError(name)
			return value


	def fill_hparams(self, fn, args=None, kwargs=None, **finder_kwargs) -> Dict[str, Any]:
		params = extract_function_signature(fn, args=args, kwargs=kwargs, allow_positional=False,
		                                    default_fn=self._find_missing_hparam(self), **finder_kwargs)

		return params


	def _extract_hparams(self, kwargs):
		for name, _ in self.named_hyperparameters():
			if name in kwargs:
				setattr(self, name, kwargs.pop(name))
		return kwargs


	def get_hparam(self, key, default: Optional[Any] = unspecified_argument):
		val = inspect.getattr_static(self, key, unspecified_argument)
		if val is unspecified_argument:
			if default is unspecified_argument:
				raise AttributeError(f'{self.__class__.__name__} has no attribute {key}')
			return default
		return val


	def has_hparam(self, key):
		return isinstance(self.get_hparam(key, None), AbstractHyperparameter)


	@classmethod
	def hyperparameters(cls, *, hidden=False):
		for key, val in cls.named_hyperparameters(hidden=hidden):
			yield val


	@classmethod
	def named_hyperparameters(cls, *, hidden=False):
		for key, val in reversed(cls.__dict__.items()):
			if isinstance(val, AbstractHyperparameter) and (hidden or not val.hidden):
				yield key, val


	@classmethod
	def inherit_hparams(cls, *names):
		for name in reversed(names):
			val = getattr(cls, name, None)
			if val is None:
				raise AttributeError(f'{cls.__name__} has no attribute {name}')
			setattr(cls, name, val)
		return cls



class ModifiableParameterized(ParameterizedBase, Modifiable):
	@classmethod
	def inject_mods(cls, *mods, name=None):
		product = super().inject_mods(*mods, name=name)
		product.inherit_hparams(*[key for src in [*reversed(mods), cls]
		                          for key, param in src.named_hyperparameters()])
		return product



class FingerprintedParameterized(ParameterizedBase, Fingerprinted):
	def _fingerprint_data(self):
		data = super()._fingerprint_data()
		hparams = {}
		for k, val in self.named_hyperparameters(hidden=True):
			try:
				hparams[k] = getattr(self, k)
			except AttributeError:
				pass
		data.update(hparams)
		return data



class InheritHparamsDecorator:
	def __init__(self, *names: Union[str, ParameterizedBase], **kwargs):
		self.names = names
		self.kwargs = kwargs


	_inherit_fn_name = 'inherit_hparams'

	def __call__(self, cls):
		try:
			inherit_fn = getattr(cls, self._inherit_fn_name)
		except AttributeError:
			raise TypeError(f'{cls} must be a subclass of {ParameterizedBase}')
		else:
			inherit_fn(*self.names, **self.kwargs)
		return cls



class HparamWrapper(method_wrapper):
	@staticmethod
	def process_args(args, kwargs, owner, instance, fn):
		base = owner if instance is None else instance
		return (), base.fill_hparams(fn, args, kwargs)













