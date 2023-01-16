import math
from collections import OrderedDict
import torch
from omnibelt import unspecified_argument, duplicate_instance, md5, agnosticmethod


from ..features import Named, Seeded, Container
from .old_abstract import AbstractData, AbstractView, AbstractBuffer
from .buffers import Buffer, AbstractCountableData, AbstractCountableDataView



class Batchable(AbstractData):
	class Progress:  # closest analogue to the DataLoader in Pytorch
		# TODO: make this exportable and fingerprinted
		def __init__(self, infinite=None, **kwargs):
			super().__init__(**kwargs)
			self.source = None
			self._batch_counter = 0
			self.infinite = infinite


		@property
		def batch_count(self):
			return self._batch_counter


		class Busy(Exception):
			def __init__(self, obj):
				super().__init__(f'{obj} has already started')
				self.obj = obj


		def __call__(self, source, infinite=None, **kwargs):
			if self.source is not None:
				# each Progress instance should only be used for iterating through data once
				raise self.Busy(self)
			self.source = source
			if self.infinite is None:
				self.infinite = infinite
			self._sels_source = self._sels_iterator(infinite=infinite, **kwargs)
			return self


		def _generate_selections(self, **kwargs):
			return self.source.generate_selections(**kwargs)


		def _sels_iterator(self, **kwargs):
			while True:
				for sel in self._generate_selections(**kwargs):
					yield sel
				if not self.infinite:
					break


		def _create_batch(self, sel, **kwargs):
			return self.source.create_batch(sel=sel, progress=self)


		def new_batch(self):
			batch = self._create_batch(next(self._sels_source))
			self._batch_counter += 1
			return batch


		def __iter__(self):
			return self


		def __next__(self):
			return self.new_batch()


	def get_iterator(self, infinite=False, progress=None, **kwargs):
		if progress is None:
			progress = self.Progress()
		return progress(self, infinite=infinite, **kwargs)


	def __iter__(self):
		return self.get_iterator()


	def get_batch(self, **kwargs):
		return next(self.get_iterator(**kwargs))


	def __next__(self):
		return self.get_batch()


	def generate_selections(self, **kwargs):
		raise NotImplementedError


	class NoBatch(AbstractData.NoView):
		pass


	Batch = None
	def create_batch(self, sel=None, progress=None, **kwargs):
		if self.Batch is None:
			raise self.NoBatch
		return self.Batch(source=self, sel=sel, progress=progress, **kwargs)



class Epoched(AbstractCountableData, Batchable, Seeded): # TODO: check Seeded and Device integration
	'''Batchable with a fixed total number of samples (implements __len__)'''
	def __init__(self, batch_size=64, shuffle_batches=True, strict_batch_size=True, infinite=False, **kwargs):
		super().__init__(**kwargs)
		self._batch_size = batch_size
		self._strict_batch_size = strict_batch_size
		self._shuffle_batches = shuffle_batches
		self._infinite = infinite


	@property
	def batch_size(self):
		return self._batch_size
	@batch_size.setter
	def batch_size(self, batch_size):
		self._batch_size = batch_size


	@staticmethod
	def _is_big_number(N):
		return N > 10000000
	
	
	@classmethod
	def shuffle_indices(cls, N, rng=None):
		# if seed is not None and gen is None:
		# 	gen = torch.Generator()
		# 	gen.manual_seed(seed)
		# TODO: include a warning if cls._is_big_number(N)
		return torch.randint(N, size=(N,), generator=rng) \
			if cls._is_big_number(N) else torch.randperm(N, generator=rng)


	def generate_selections(self, sel=None, sample_limit=None, batch_size=None, shuffle=True,
	                        strict_batch_size=None, rng=None, **kwargs):
		if batch_size is None:
			batch_size = self.batch_size
		if strict_batch_size is None:
			strict_batch_size = self._force_batch_size
		if rng is None:
			rng = self.rng
			
		if sel is None:
			sel = torch.arange(self.size)
		if shuffle:
			sel = sel[self.shuffle_indices(len(sel), gen=rng)]
		order = sel
		if sample_limit is not None and len(order) > sample_limit:
			order = order[:max(sample_limit, batch_size) if strict_batch_size else sample_limit]
		inds = list(order.split(batch_size))
		if strict_batch_size and len(inds) and len(inds[-1]) != batch_size:
			inds.pop()
		return inds


	class Progress(Batchable.Progress, Seeded): # closest analogue to the DataLoader in Pytorch
		def __init__(self, batch_size=64, shuffle=True, strict_batch_size=True, pbar=None, pbar_samples=True, **kwargs):
			super().__init__(**kwargs)
			self._sample_counter = 0
			self._epoch_counter = 0

			self._epoch_seed = None
			self._batch_idx = None

			self.pbar = None
			self._pbar_cls = pbar
			self.pbar_samples = pbar_samples

			# "default" defaults
			self.batch_size = batch_size
			self.shuffle = shuffle
			self.strict_batch_size = True


		@staticmethod
		def compute_budget(dataset_size, samples_per_batch, strict_batch_size=True,
		                   epochs=None, sample_limit=None, batch_limit=None, strict_limit=True):
			if epochs is None and sample_limit is None and batch_limit is None:
				return None, None, None # infinite

			samples_per_epoch = dataset_size - int(strict_batch_size) * (dataset_size % samples_per_batch)
			batches_per_epoch = int(math.ceil(samples_per_epoch / samples_per_batch))

			total_samples = None if epochs is None else samples_per_epoch * epochs
			if batch_limit is not None:
				total = (batch_limit % batches_per_epoch) * samples_per_batch \
				                + (batch_limit // batches_per_epoch) * samples_per_epoch
				if total_samples is None or total < total_samples:
					total_samples = total
			if sample_limit is not None:
				total = samples_per_epoch * (sample_limit // samples_per_epoch)
				remainder = sample_limit % samples_per_epoch
				total += samples_per_batch * (remainder // samples_per_batch)
				remainder = remainder % samples_per_batch
				if strict_limit and not strict_batch_size:
					total += remainder
				elif not strict_limit:
					total += samples_per_batch
				if total_samples is None or total < total_samples:
					total_samples = total

			full_epochs = total_samples // samples_per_epoch
			remainder = total_samples % samples_per_epoch
			total_batches = full_epochs * batches_per_epoch + remainder // samples_per_batch
			remainder = remainder % samples_per_batch
			if not strict_batch_size and remainder > 0:
				total_batches += 1

			return total_samples, total_batches, full_epochs


		def __call__(self, source, epochs=None, sample_limit=None, batch_limit=None, infinite=None,
	                 batch_size=None, shuffle=None, strict_batch_size=None, strict_limit=True,
	                 gen=None, sel=None, pbar=unspecified_argument, pbar_samples=None, **kwargs):
			if self.shuffle is None:
				self.shuffle = shuffle
			if self.batch_size is None:
				self.batch_size = batch_size
			if strict_batch_size is not None:
				self.strict_batch_size = strict_batch_size
			if epochs is None and sample_limit is None and batch_limit is None:
				epochs = 1 # by default, iterate through a whole epoch

			self.total_samples, self.total_batches, self.full_epochs = self.compute_budget(
				dataset_size=source.size if sel is None else len(sel),
				samples_per_batch=batch_size, strict_batch_size=strict_batch_size,
				epochs=epochs, sample_limit=sample_limit, batch_limit=batch_limit,
				strict_limit=strict_limit,
			)

			if pbar is unspecified_argument:
				pbar = self._pbar_cls
			if self.pbar_samples is None:
				self.pbar_samples = pbar_samples
			if self.pbar is not None:
				self.pbar.close()
			self.pbar = None if pbar is None \
				else pbar(total=self.total_samples if self.pbar_samples else self.total_batches,
				          unit='smpl' if self.pbar_samples else 'batch')

			out = super().__call__(source, infinite=infinite, sel=sel, gen=gen, shuffle=shuffle,
			                       batch_size=batch_size, strict_batch_size=strict_batch_size, **kwargs)
			if self.infinite:
				self.total_samples, self.total_batches, self.full_epochs = None, None, None
			return out


		def new_batch(self):
			batch = super().new_batch()
			self._sample_counter += batch.size
			if self.pbar is not None:
				self.pbar.update(batch.size if self.pbar_samples else 1)
			# if self.callback is not None:
			# 	out = self.callback(self, batch)
			# 	if out is not None: # TODO: maybe clean up or include warnings somewhere (+ lots of docs)
			# 		batch = out
			return batch


		def set_description(self, desc):
			if self.pbar is not None:
				self.pbar.set_description(desc)


		def _generate_selections(self, **kwargs):
			sels = self.source.generate_selections(**kwargs)
			if self._batch_idx is not None:
				sels = sels[self._batch_idx:]
			return sels


		def _sels_iterator(self, gen=None, **kwargs): # this function contains the actual loop
			if gen is None:
				gen = self.gen
			while not self.done:
				epoch_gen = self.create_rng(seed=self._epoch_seed, base_gen=gen)
				self._epoch_seed = epoch_gen.initial_seed()
				sels = self._generate_selections(sample_limit=self.total_samples, gen=epoch_gen, **kwargs)
				if self._batch_idx is None:
					self._batch_idx = 0
				for sel in sels:
					self._batch_idx += 1
					yield sel
				self._epoch_seed = None
				self._batch_idx = None
				if not self.infinite:
					break
			if self.pbar is not None:
				self.pbar.close()


		@property
		def sample_count(self):
			return self._sample_counter


		@property
		def current_epoch(self):
			return self._epoch_counter


		@property
		def completed_epochs(self):
			return self.current_epoch - 1


		@property
		def remaining_epochs(self):
			if self.full_epochs is None:
				return float('inf')
			return self.full_epochs - self.current_epoch


		@property
		def remaining_samples(self):
			if self.total_samples is None:
				return float('inf')
			return self.total_samples - self.sample_count


		@property
		def remaining_batches(self):
			if self.total_batches is None:
				return float('inf')
			return self.total_batches - self.batch_count


		@property
		def done(self):
			return self.remaining_samples <= 0 or self.remaining_batches <= 0


	def get_iterator(self, epochs=None, sample_limit=None, batch_limit=None, infinite=None,
	                 batch_size=None, shuffle=None, strict_batch_size=None, strict_limit=True,
	                 gen=None, sel=None, pbar=unspecified_argument, pbar_samples=None, progress=None, **kwargs):
		if batch_size is None:
			batch_size = self.batch_size
		if strict_batch_size is None:
			strict_batch_size = self._strict_batch_size
		if shuffle is None:
			shuffle = self._shuffle_batches
		if gen is None:
			gen = self.gen

		return super().get_iterator(epochs=epochs, sample_limit=sample_limit, batch_limit=batch_limit,
		                            infinite=infinite, batch_size=batch_size, shuffle=shuffle,
		                            strict_batch_size=strict_batch_size, strict_limit=strict_limit, gen=gen, sel=sel,
		                            pbar=pbar, pbar_samples=pbar_samples, progress=progress, **kwargs)
			
		# subsel = sel
		#
		# N = self.size if subsel is None else len(subsel)
		# samples_per_epoch = N - int(force_batch_size) * (N % batch_size)
		# batches_per_epoch = int(math.ceil(samples_per_epoch / batch_size))
		# if infinite is None:
		# 	total_samples = None
		# elif num_batches is not None:
		# 	total_samples = (num_batches % batches_per_epoch) * batch_size \
		# 	                + (num_batches // batches_per_epoch) * samples_per_epoch
		# elif num_samples is not None:
		# 	total_samples = samples_per_epoch * (num_samples // samples_per_epoch)
		# 	remainder = num_samples % samples_per_epoch
		# 	total_samples += batch_size * (remainder // batch_size)
		# 	remainder = remainder % batch_size
		# 	if not hard_limit or not force_batch_size:
		# 		total_samples += remainder
		# else:
		# 	total_samples = samples_per_epoch * epochs
		# if pbar is not None:
		# 	pbar = pbar(total=total_samples if pbar_samples else total_samples // batch_size,
		# 	            unit='smpl' if pbar_samples else 'batch')
		#
		# while total_samples is None or total_samples > 0:
		# 	sels = self.generate_selections(sel=subsel, sample_limit=total_samples, batch_size=batch_size,
		# 	                                shuffle=shuffle, force_batch_size=force_batch_size, gen=gen, **kwargs)
		# 	for sel in sels:
		# 		N = len(sel)
		# 		if total_samples is not None:
		# 			total_samples -= N
		# 			if hard_limit and total_samples < 0:
		# 				break
		# 		if pbar is not None:
		# 			pbar.update(N if pbar_samples else 1)
		# 		yield self.create_batch(sel=sel, pbar=pbar)
		# 		if total_samples is not None and total_samples <= 0:
		# 			break
		# if pbar is not None:
		# 	pbar.close()



class DataSource(Batchable, AbstractData, Named):
	class MissingBuffer(Exception):
		pass


	def available_buffers(self): # returns list of names
		raise NotImplementedError


	def iter_buffers(self): # iterates through buffers
		raise NotImplementedError


	def iter_named_buffers(self):
		raise NotImplementedError


	def register_buffer(self, name, buffer, **kwargs):
		raise NotImplementedError


	def get_buffer(self, name):
		raise NotImplementedError


	def has_buffer(self, name):
		raise NotImplementedError


	def __getitem__(self, name):
		return self.get(name)


	def __contains__(self, item):
		return self.has_buffer(item)


	def space_of(self, name):
		return self.get_buffer(name).space


	def get(self, name, sel=None, **kwargs):
		if not self.is_ready:
			raise self.NotReady(f'{self} has not been prepared (call .prepare() first)')
		return super().get(sel=sel, name=name, **kwargs)


	def _get(self, name, sel=None, **kwargs):
		return self.get_buffer(name).get(sel)
		buffer = self.get_buffer(name)
		data = buffer.get(sel)
		return data


	def _prepare(self, *args, **kwargs):
		for name, buffer in self.iter_named_buffers():
			buffer.prepare()


	def _title(self):
		return self.name



class SourceView(DataSource, AbstractView):
	# _is_ready = True

	View = None


	def _title(self):
		return '' if self.source is None else self.source._title()


	def __str__(self):
		src = '{' + self._title() + '}'
		return f'{self.__class__.__name__}{src}'#"{hex(id(self))[2:]}"'


	# def get(self, name, sel=unspecified_argument, **kwargs):
	# 	if sel is unspecified_argument:
	# 		sel = self.sel
	# 	return super().get(sel=sel, name=name, **kwargs)


	def _get(self, name, sel=None, **kwargs):
		if self.source is None:
			raise self.NoSource
		sel = self._merge_sel(sel)
		return self.source.get(name, sel=sel, **kwargs)
		# return self.get_buffer(name).get(sel)
		buffer = self.get_buffer(name)
		data = buffer.get(sel)
		return data


	def _prepare(self, *args, **kwargs):
		if self.source is not None:
			self.source.prepare()


	def _update(self, sel=None, **kwargs):
		if self.source is None:
			raise self.NoSource
		sel = self._merge_sel(sel)
		return self.source.update(sel=sel, **kwargs)


	Batch = None
	def create_batch(self, sel=None, **kwargs):
		if self.Batch is None:
			if self.source is None:
				raise self.NoSource
			return self.source.create_batch(**kwargs)
		return super().create_batch(**kwargs)


	def available_buffers(self): # returns list of names
		if self.source is None:
			raise self.NoSource
		return self.source.available_buffers()


	def get_buffer(self, name):
		if self.source is None:
			raise self.NoSource
		return self.source.get_buffer(name)


	def has_buffer(self, name):
		if self.source is None:
			raise self.NoSource
		return self.source.has_buffer(name)



DataSource.View = SourceView



class MultiModed(DataSource):
	def __init__(self, *, mode=None, modes=None, **kwargs):
		super().__init__(**kwargs)
		if modes is None:
			modes = OrderedDict()
		self._modes = modes
		self._mode = mode


	def copy(self):
		new = super().copy()
		new._modes = new._modes.copy()
		return new


	def register_modes(self, **modes):
		for name, mode in modes.items():
			mode._mode = name
		self._modes.update(modes)


	@property
	def mode(self):
		return self._mode


	def _fingerprint_data(self):
		return {'mode': self.mode, **super()._fingerprint_data()}


	class MissingModeError(Exception):
		pass


	def get_mode(self, mode='train'):
		if self.mode == mode:
			return self
		if mode in self._modes:
			return self._modes[mode]
		raise self.MissingModeError



class BufferTable(DataSource):
	def __init__(self, buffers=None, **kwargs):
		super().__init__(**kwargs)
		if buffers is None:
			buffers = OrderedDict()
		self.buffers = buffers


	def available_buffers(self): # returns list of names
		return list(self.buffers.keys())


	def iter_buffers(self):
		for k, v in self.iter_named_buffers():
			yield v


	def iter_named_buffers(self): # iterates through buffers
		for k, v in self.buffers.items():
			if not isinstance(v, str):
				yield k, v


	def get_buffer(self, name):
		if name not in self.buffers:
			raise self.MissingBuffer(name)
		buffer = self.buffers[name]
		if isinstance(buffer, str):
			return self.get_buffer(buffer)
		return buffer


	def has_buffer(self, name):
		return name in self.buffers


	def _fingerprint_data(self):
		data = super()._fingerprint_data()
		if self.is_ready:
			data['buffers'] = {}
			for name, buffer in self.iter_named_buffers():
				data['buffers'][name] = buffer.fingerprint()
		return data
		return {'buffers': {name:buffer.fingerprint() for name, buffer in self.iter_named_buffers()}, 'ready': self.is_ready,
		        **super()._fingerprint_data()}


	def copy(self):
		new = super().copy()
		new.buffers = new.buffers.copy()
		return new


	class InvalidBuffer(Exception):
		def __init__(self, name, buffer):
			super().__init__(f'{name}: {buffer}')
			self.name, self.buffer = name, buffer


	Buffer = Buffer
	@classmethod
	def _create_buffer(cls, **kwargs):
		return cls.Buffer(**kwargs)


	def register_buffer(self, name, buffer=None, space=unspecified_argument, **kwargs):
		if isinstance(buffer, str):
			assert space is unspecified_argument, 'cant specify a space for an alias'
		elif not isinstance(buffer, AbstractBuffer):
		# elif buffer is None or isinstance(buffer, torch.Tensor):
			if type(buffer) == type and issubclass(buffer, AbstractBuffer):
				if space is not unspecified_argument:
					kwargs['space'] = space
				buffer = buffer(**kwargs)
			else:
				kwargs['data'] = buffer
				if space is not unspecified_argument:
					kwargs['space'] = space
				buffer = self._create_buffer(**kwargs)
		if space is not unspecified_argument:
			buffer.space = space
		if not isinstance(buffer, str) and not self._check_buffer(name, buffer):
			raise self.InvalidBuffer(name, buffer)
		self.buffers[name] = buffer
		return self.buffers[name]


	def _check_buffer(self, name, buffer): # during registration
		return True


	def _remove_buffer(self, name):
		if name in self.buffers:
			del self.buffers[name]


	def rename_buffer(self, current, new=None):
		buffer = self.get_buffer(current)
		if buffer is not None:
			self._remove_buffer(current)
		if new is not None:
			self.register_buffer(new, buffer)



class ReplacementView(BufferTable, SourceView): # TODO: shouldnt the order be (SourceView, BufferTable) ?
	def available_buffers(self):
		buffers = super().available_buffers()
		for replacement in super(BufferTable, self).available_buffers():
			if replacement not in buffers:
				buffers.append(replacement)
		return buffers


	def get_buffer(self, name):
		if name in self.buffers:
			return super().get_buffer(name)
		return super(BufferTable, self).get_buffer(name)


	def _get(self, name, sel=None, **kwargs):
		if name in self.buffers:
			sel = self._merge_sel(sel)
			return super(SourceView, self)._get(name, sel=sel, **kwargs)
		return super()._get(name, sel=sel, **kwargs)
		# if self.source is None:
		# 	raise self.NoSource
		# sel = self._merge_sel(sel)
		# return self.source.get(name, sel=sel, **kwargs)
		# # return self.get_buffer(name).get(sel)
		# buffer = self.get_buffer(name)
		# data = buffer.get(sel)
		# return data



	# Buffer = ReplacementBuffer
	# def register_buffer(self, name, buffer=None, space=unspecified_argument, **kwargs):
	# 	buffer = super().register_buffer(name=name, buffer=buffer, space=space, **kwargs)
	# 	# TODO: change or include the source information for replacement buffers
	# 	buffer.source_table = self.source
	# 	buffer.source_key = name
	# 	return buffer


	def _update(self, sel=None, **kwargs):
		# if name in self.buffers:
		# 	return super(SourceView, self)._update(name, sel=sel, **kwargs)
		if self.source is None:
			raise self.NoSource
		sel = self._merge_sel(sel)
		return self.source.update(sel=sel, **kwargs)


	def has_buffer(self, name):
		return name in self.buffers or name in super(BufferTable, self).has_buffer(name)



class CountableView(AbstractCountableDataView, Epoched, SourceView):
	def get_iterator(self, *, sel=None, **kwargs):
		sel = self._merge_sel(sel)
		return super().get_iterator(sel=sel, **kwargs)


	def generate_selections(self, *, sel=None, **kwargs):
		sel = self._merge_sel(sel)
		return super().generate_selections(sel=sel, **kwargs)



class CachedView(SourceView, Container):
	def __init__(self, progress=None, **kwargs):
		super().__init__(**kwargs)
		self.progress = progress


	# def set_description(self, desc):
	# 	if self._progress is not None:
	# 		self._progress.set_description(desc)


	def is_cached(self, item):
		return super(DataSource, self).__contains__(item)


	def __contains__(self, item):
		return self.is_cached(item) or (self.source is not None and item in self.source)


	def __getitem__(self, name):
		return super(DataSource, self).__getitem__(name)


	def __len__(self):
		return super(AbstractCountableData, self).__len__()


	def update(self, other): # TODO: maybe add a warning that dict.update is used
		return super(AbstractData, self).update(other)


	def get(self, name, default=None, **kwargs):
		if self.is_cached(name):
			return super(AbstractData, self).get(name, default)
		elif name in self:
			val = super().get(name, **kwargs)
			# if self.device is not None:
			# 	val = val.to(self.device)
			self[name] = val
			return self[name]
		return default


	def _find_missing(self, key, **kwargs):
		val = self.get(key, default=unspecified_argument, **kwargs)
		if val is unspecified_argument:
			return super()._find_missing(key)
		return val



Batchable.Batch = CachedView



class DataCollection(MultiModed, BufferTable, DataSource):
	def __init__(self, data={}, **kwargs):
		super().__init__(**kwargs)
		for key, val in data.items():
			self.register_buffer(key, val)


	def _title(self):
		mode = self.mode
		mode = '' if mode is None else f'<{mode}>'
		return f'{super()._title()}{mode}'


	def _update(self, sel=None, **kwargs):
		for name, buffer in self.iter_named_buffers(True):
			buffer.update(sel=sel, **kwargs)



class Subsetable(Epoched):
	@staticmethod
	def _split_indices(indices, cut):
		assert cut != 0
		last = cut < 0
		cut = abs(cut)
		total = len(indices)
		if isinstance(cut, float):
			assert 0 < cut < 1
			cut = int(cut * total)
		part1, part2 = indices[:cut], indices[cut:]
		if last:
			part1, part2 = part2, part1
		return part1, part2


	def subset(self, cut=None, sel=None, shuffle=False, hard_copy=True, gen=None):
		if sel is None:
			sel, _ = self._split_indices(indices=self.shuffle_indices(self.size, gen=gen)
			if shuffle else torch.arange(self.size), cut=cut)
		return self.create_view(sel=sel)


	def split(self, splits, shuffle=False, gen=None):
		if gen is None:
			gen = self.gen
		auto_name = isinstance(splits, (list, tuple, set))
		if auto_name:
			named_cuts = [(f'part{i}', r) for i, r in enumerate(splits)]
		else:
			assert isinstance(splits, dict), f'unknown splits: {splits}'
			assert not any(x for x in splits if x is None), 'names of splits cannot be None'
			named_cuts = list(splits.items())
		names, cuts = zip(*sorted(named_cuts, key=lambda nr: (isinstance(nr[1], int), isinstance(nr[1], float),
		                                                      nr[1] is None, nr[0]), reverse=True))

		remaining = self.size
		nums = []
		itr = iter(cuts)
		for cut in itr:
			if isinstance(cut, int):
				nums.append(cut)
				remaining -= cut
			else:
				if isinstance(cut, float):
					ratios = []
					while isinstance(cut, float):
						ratios.append(cut)
						cut = next(itr, 'done')
					if len(cuts):
						rationums = [int(remaining * abs(ratio)) for ratio in ratios]
						nums.extend([int(math.copysign(1, r) * n) for r, n in zip(ratios, rationums)])
						remaining -= sum(rationums)
				if cut is None:
					pieces = len([cut, *itr])
					assert remaining > pieces, f'cant evenly distribute {remaining} samples into {pieces} cuts'
					evennums = [int(remaining // pieces) for _ in range(pieces)]
					nums.extend(evennums)
					remaining -= sum(evennums)

		if remaining > 0:
			nums[-1] += remaining

		indices = self.shuffle_indices(self.size, gen=gen) if shuffle else torch.arange(self.size)

		plan = dict(zip(names, nums))
		parts = {}
		for name in sorted(names):
			num = plan[name]
			part, indices = self._split_indices(indices, num)
			parts[name] = self.subset(sel=part)
		if auto_name:
			return [parts[name] for name, _ in named_cuts]
		return parts



class Batch(Subsetable, CountableView, CachedView):
	pass



class View(Subsetable, CountableView, ReplacementView):
	pass


from .. import Sampler


class Dataset(Subsetable, DataCollection, Sampler):
	def __init__(self, **kwargs):
		super().__init__(**kwargs)
		self._subset_src = None
	# 	# self._waiting_subset = None
	# 	# self._subset_indices = None


	View = View
	Batch = Batch


	sample_key = None

	def _sample(self, shape, gen, sample_key=unspecified_argument):
		if sample_key is unspecified_argument:
			sample_key = self.sample_key
		N = shape.numel()
		batch = self.get_batch(shuffle=True, sample_limit=N, batch_size=N, gen=gen)
		if self.sample_key is None:
			return batch
		return batch[sample_key].view(*shape, *self.space_of(sample_key).shape)


	# def _fingerprint_data(self):
	# 	data = super()._fingerprint_data()
	# 	N = len(self)
	# 	data['len'] = N
	# 	if N > 0:
	# 		sel = torch.randint(N, size=(min(5,N),), generator=self.create_rng(seed=16283393149723337453))
	# 		for name, buffer in self.iter_named_buffers(True):
	# 			if self.is_ready:
	# 				try:
	# 					data[name] = self.get(name, sel=sel).view(len(sel), -1).sum(-1).tolist()
	# 				except:
	# 					raise # TESTING
	# 			data[f'{name}-space'] = buffer.space
	# 	return data


	def _length(self):
		return next(iter(self.iter_buffers(True))).length()


	def get_subset_src(self, recursive=True):
		if self._subset_src is None:
			return self
		return self._subset_src.get_subset_src(recursive=recursive) if recursive else self._subset_src


	@staticmethod
	def _create_buffer_view(buffer, sel=None, **kwargs):
		return buffer.create_view(sel=sel, **kwargs)


	def subset(self, cut=None, sel=None, shuffle=False, src_ref=True, hard_copy=True, gen=None):
		if hard_copy:
			if sel is None:
				sel, _ = self._split_indices(indices=self.shuffle_indices(self.size, gen=gen)
				if shuffle else torch.arange(self.size), cut=cut)
			new = self.copy()
			if src_ref:
				new._subset_src = self
			new._default_len = len(sel)
			for name, buffer in self.buffers.items():
				new.register_buffer(name, buffer if isinstance(buffer, str)
				else self._create_buffer_view(buffer, sel=sel))
		else:
			new = super().subset(cut=cut, sel=sel, shuffle=shuffle, gen=gen)
		if self.mode is not None:
			self.register_modes(**{self.mode: new})
		return new

	
	def split(self, splits, shuffle=False, register_modes=False):
		parts = super().split(splits, shuffle=shuffle)
		if register_modes and isinstance(splits, dict):
			self.register_modes(**parts)
		return parts








