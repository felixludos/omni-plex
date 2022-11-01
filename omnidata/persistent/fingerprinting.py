from typing import Union, Any, Callable, Type, Iterable, Iterator, Optional, List, Dict, Tuple, Sequence, Hashable
from pathlib import Path
import numpy as np
import torch
from omnibelt import unspecified_argument, agnosticmethod, md5, primitive, JSONABLE
from omnibelt import Exportable, ExportManager


from ..structure import Extractor

# TODO: make exportable
# .fp -> hash
# .fpd -> data


class AbstractFingerprinted:
	@property
	def fingerprint(self):
		raise NotImplementedError



class AbstractFingerprint(AbstractFingerprinted, Exportable, Extractor):
	@property
	def fingerprint(self):
		return self

	class ExtractionError(ValueError):
		def __init__(self, obj):
			super().__init__(obj)
			self.obj = obj

	# @staticmethod
	# def _obj_type(obj):
	# 	if isinstance(obj, type):
	# 		return f'!type:{obj.__module__}.{obj.__name__}'
	# 	obj = type(obj)
	# 	return f'{obj.__module__}.{obj.__name__}'

	@classmethod
	def extract(cls, obj, force_str=False) -> JSONABLE:
		if force_str:
			if not isinstance(obj, str):
				raise cls.ExtractionError(obj)
			return str(obj)
		if isinstance(obj, primitive):
			return obj
		# if isinstance(obj, (np.ndarray, torch.Tensor)):
		# 	numels = np.product(obj.shape).item()
		# 	sel = torch.randint(numels, size=(min(5, numels),),
		# 	        generator=torch.Generator().manual_seed(16283393149723337453)).tolist()
		# 	return [str(obj.shape), str(obj.dtype), obj.sum().item(), obj.reshape(-1)[sel].tolist()]
		if isinstance(obj, (list, tuple)):
			return [cls.extract(o) for o in obj]
		if isinstance(obj, dict):
			return {cls.extract(k, force_str=True): cls.extract(v) for k, v in obj.items()}
		raise cls.ExtractionError(obj)

	def __eq__(self, other):
		return isinstance(other, AbstractFingerprint) and self.check_fingerprint(other)

	def __hash__(self):
		return hash(self.code())

	def code(self):
		return md5(self.data())

	def data(self):
		raise NotImplementedError

	class UnknownObjectError(TypeError):
		pass

	def check_fingerprint(self, obj: Union['AbstractFingerprint', AbstractFingerprinted]):
		if isinstance(obj, AbstractFingerprinted):
			return self == obj.fingerprint
		if not isinstance(obj, AbstractFingerprint):
			raise self.UnknownObjectError(obj)
		return self.code() == obj.code()



class Fingerprinted(AbstractFingerprinted):
	class Fingerprint(AbstractFingerprint, extensions=['fp', 'fpd']):
		def __init__(self, src=None, *, data=None, code=None, **kwargs):
			super().__init__(src=src, **kwargs)
			self.src = src
			self._data = data
			self._code = code

		@classmethod
		def _load_export(cls, path: Path, src: Type['ExportManager']) -> Any:
			if path.suffix == '.fpd':
				return cls(data=src.load_export(fmt='json', path=path))
			return cls(code=path.read_text())

		@staticmethod
		def _export_payload(payload: 'AbstractFingerprint', path: Path, src: Type['ExportManager']) -> Optional[Path]:
			if path.suffix == '.fpd':
				return src.export(payload.data(), fmt='json', path=path, sort_keys=True)
			path.write_text(payload.code())
			return path

		@classmethod
		def extract(cls, obj, **kwargs) -> JSONABLE:
			if isinstance(obj, Fingerprinted):
				return cls.extract(obj._fingerprint_data(), **kwargs)
			return super().extract(obj, **kwargs)


		class NoObjectError(AttributeError):
			pass

		@property
		def src(self):
			src = getattr(self, '_src', None)
			if src is None:
				raise self.NoObjectError(src)
			return src
		@src.setter
		def src(self, src):
			self._src = src

		def data(self):
			if self._data is None:
				self._data = self.extract(self.src)
			return self._data

		def code(self):
			if self._code is None:
				self._code = super().code()
			return self._code

	@property
	def fingerprint(self):
		return self.Fingerprint(self)

	def _fingerprint_data(self):
		return {'cls': self.__class__.__name__, 'module': self.__module__}






