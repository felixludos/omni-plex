from .imports import *
from .abstract import *



class MissingValueError(AttributeError):
	def __init__(self, descriptor: Any, message: Optional[str] = None):
		if message is None:
			message = f'{descriptor}'
		super().__init__(message)



class MissingOwnerError(TypeError):
	def __init__(self, descriptor: Any, message: Optional[str] = None):
		if message is None:
			message = f'Cannot delete {descriptor} without providing an instance.'
		super().__init__(message)



class IgnoreResetFlag(Exception):
	pass



class ToolFailedError(Exception):
	def __init__(self, gizmo: str, *, message: Optional[str] = None):
		if message is None:
			message = f'{gizmo!r}'
		super().__init__(message)
		self.gizmo = gizmo


	def reason(self):
		return 'failed'



class AssemblyFailedError(ToolFailedError):
	def __init__(self, gizmo: str, failures: List[Tuple[AbstractTool, ToolFailedError]], *,
	             message: Optional[str] = None):
		if message is None:
			message = self.verbalize_failures(gizmo, failures)
		super().__init__(gizmo, message=message)
		self.gizmo = gizmo
		self.failures = failures


	def reason(self):
		return f'tried {len(self.failures)} tool/s'


	@staticmethod
	def verbalize_failures(gizmo: str, failures: List[Tuple[AbstractTool, ToolFailedError]]):
		path = [e.gizmo for tool, e in failures]
		terminal = failures[-1][1].reason()
		return f'Failed to assemble {gizmo!r} due to {" -> ".join(path)} ({terminal!r})'



class MissingGizmoError(ToolFailedError, KeyError):
	def __init__(self, gizmo: str, *, message: Optional[str] = None):
		if message is None:
			message = gizmo
		super().__init__(gizmo, message=message)


	def reason(self):
		return 'missing'



# class SkipToolFlag(ToolFailedError):
# 	'''raised by a tool to indicate that it should be skipped'''
# 	pass









