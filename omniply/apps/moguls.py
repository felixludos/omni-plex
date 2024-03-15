from typing import Any, Iterable, Iterator

from ..core.gaggles import AbstractGaggle, LoopyGaggle, MutableGaggle
from ..core import Context, ToolKit



class AbstractMogul(AbstractGaggle):
	def announce(self, item: Any):
		'''packages the item for consumption (which usually means converting it to a Gig e.g. Context)'''
		raise NotImplementedError


	def __iter__(self):
		raise NotImplementedError



class MogulIterator:
	def __init__(self, mogul: AbstractMogul, stream: Iterator[Any]):
		self.mogul = mogul
		self.stream = stream


	def __iter__(self):
		return self


	def __next__(self):
		item = next(self.stream)
		return self.mogul.announce(item)



class StreamMogul(ToolKit, AbstractMogul):
	_context_type = Context
	_iterator_type = MogulIterator

	def announce(self, item: Any):
		return self._context_type(item).include(self)


	def _generate_stream(self):
		raise NotImplementedError


	def __iter__(self):
		return self._iterator_type(self, self._generate_stream())












