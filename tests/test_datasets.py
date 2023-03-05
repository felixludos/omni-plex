import sys, os
import yaml

import torch

import omnidata as od
from omnidata import toy

def _cmp_dicts(d1, d2):
	return yaml.dump(d1, sort_keys=True) == yaml.dump(d2, sort_keys=True)


dataset = None
def _init_default_dataset():
	global dataset
	if dataset is None:
		dataset = toy.SwissRollDataset(100, seed=16283393149723337453)
	return dataset



def test_dataset_init():
	dataset = _init_default_dataset()

	print()
	print(dataset)

	assert dataset.size == 100



# def test_dataset_init():
# 	dataset = _init_default_dataset()
#
# 	assert dataset.size == 100
#
# 	assert str(dataset) == 'SwissRollDataset[100](observation, target, mechanism)'
#
# 	buffers = tuple(sorted(dataset.available_buffers()))
# 	assert len(buffers) == len(dataset)
# 	assert buffers == ('mechanism', 'observation', 'target')
#
# 	assert str(dataset.observation_space) \
# 	       == 'Joint(Bound(min=-14.1, max=14.1), Bound(min=0, max=21), Bound(min=-14.1, max=14.1))'
# 	assert str(dataset.target_space) == 'Bound(min=3, max=9)'
# 	assert str(dataset.mechanism_space) == 'Joint(Bound(min=3, max=9), Bound(min=0, max=1))'
#
# 	assert dataset.observation_space.shape == (3,)
# 	assert dataset.target_space.shape == ()
# 	assert dataset.mechanism_space.shape == (2,)
#
#
# def test_dataset_fingerprint():
# 	dataset = _init_default_dataset()
#
# 	assert dataset.fingerprint.code() == 'dbe51ff6144ae53dadb46e33553c1a3d'
#
# 	assert _cmp_dicts(dataset.fingerprint.data(),
# 	                  {'cls': 'SwissRollDataset',
# 	                   'module': 'omnidata.data.toy.manifolds',
# 	                   'batch_size': 5,
# 	                   'tmax': 9.0, 'tmin': 3.0, 'freq': 0.5,
# 	                   'Az': 1.5707963267948966, 'Ay': 21.0, 'Ax': 1.5707963267948966,
# 	                   'n_samples': 100
# 	                   })
#
#
# def test_dataset_prepare():
# 	dataset = _init_default_dataset()
#
# 	assert dataset.is_ready == False
#
# 	dataset.prepare()
#
# 	assert dataset.is_ready == True
#
#
# def test_dataset_iteration():
# 	dataset = toy.SwissRollDataset(12, batch_size=5).prepare()
#
# 	loader = dataset.iterate(epochs=1).prepare()
# 	assert loader.remaining_batches == 3
#
# 	assert loader.current_batch is None
#
# 	batch = loader.get_batch()
# 	assert str(batch) == 'Batch[5]<SwissRollDataset[12]>({observation}, {target}, {mechanism})'
#
# 	assert batch.progress is loader
#
# 	assert loader.batch_count == 1
# 	assert loader.sample_count == 5
# 	assert loader.current_epoch == 1
#
# 	assert loader.remaining_samples == 7
# 	assert loader.remaining_batches == 2
#
#
# 	loader = dataset.iterate(sample_limit=16).prepare()
# 	assert not loader.done
# 	assert tuple(batch.size for batch in loader) == (5, 5, 2, 5)
# 	assert loader.done
# 	assert loader.batch_count == 4
# 	assert loader.sample_count == 17
# 	assert loader.current_epoch == 2
#
# 	loader = dataset.iterate(sample_limit=16, strict_batch_size=True).prepare()
# 	assert tuple(batch.size for batch in loader) == (5, 5, 5, 5)
# 	assert loader.batch_count == 4
# 	assert loader.sample_count == 20
# 	assert loader.current_epoch == 2
#
# 	loader = dataset.iterate(sample_limit=16, strict_batch_size=True, strict_limit=True).prepare()
# 	assert tuple(batch.size for batch in loader) == (5, 5, 5)
# 	assert loader.completed_epochs == 1
# 	assert loader.batch_count == 3
# 	assert loader.sample_count == 15
# 	assert loader.current_epoch == 2
#
#
# 	loader = dataset.iterate(sample_limit=16, strict_limit=True).prepare()
# 	assert tuple(batch.size for batch in loader) == (5, 5, 2, 4)
# 	assert loader.batch_count == 4
# 	assert loader.sample_count == 16
# 	assert loader.current_epoch == 2
#
#
#
# def test_dataset_batch():
# 	dataset = _init_default_dataset()
#
# 	assert dataset['observation'].shape == (100, 3) and dataset['observation'].dtype == torch.float32
#
# 	batch = dataset.batch(10)
#
# 	assert str(batch) == 'Batch[10]<SwissRollDataset[100]>({observation}, {target}, {mechanism})'
#
# 	buffers = tuple(sorted(batch.available_buffers()))
# 	assert len(buffers) == len(batch)
# 	assert buffers == ('mechanism', 'observation', 'target')
#
# 	assert str(batch.space_of('observation')) \
# 	       == 'Joint(Bound(min=-14.1, max=14.1), Bound(min=0, max=21), Bound(min=-14.1, max=14.1))'
# 	assert str(batch.space_of('target')) == 'Bound(min=3, max=9)'
# 	assert str(batch.space_of('mechanism')) == 'Joint(Bound(min=3, max=9), Bound(min=0, max=1))'
#
# 	assert tuple(batch.cached()) == ()
#
# 	obs = batch['observation']
# 	assert obs.shape == (10, 3)
# 	assert obs.dtype == torch.float32
# 	assert obs.sum().item() == 92.62188720703125
#
# 	assert tuple(sorted(batch.cached())) == ('observation',)
#
# 	obs2 = batch.get('observation')
# 	assert obs.sub(obs2).abs().sum().item() == 0
#
# 	obs3 = batch.get('obs', None)
# 	assert obs3 is None
#
#
# def test_iterate_batch():
# 	dataset = _init_default_dataset()
#
# 	batch = dataset.batch(10)
#
# 	# TODO: check batch.new()
#
# 	loader = batch.iterate(epochs=1, batch_size=5).prepare()
#
# 	b1 = loader.get_batch()
#
# 	b2, = list(loader)
#
# 	assert b1.size == 5
#
# 	assert str(b1) == 'Batch[5]<Batch[10]<SwissRollDataset[100]>>({observation}, {target}, {mechanism})'
#
# 	# TODO: more testing with b.o.b.
#
# 	t1 = b1['target'].sum()
#
# 	assert str(batch) == 'Batch[10]<SwissRollDataset[100]>({observation}, target, {mechanism})'
# 	assert str(b1) == 'Batch[5]<Batch[10]<SwissRollDataset[100]>>({observation}, target, {mechanism})'
#
# 	t2 = b2['target'].sum()
#
# 	assert batch['target'].sum().isclose(t1 + t2)
#
#
# def test_new_batches():
# 	dataset = _init_default_dataset()
#
# 	batch = dataset.batch(20)
#
# 	itr1 = [b for b in batch.iterate(batch_size=5)]
#
# 	itr2 = []
# 	i = 0
# 	for b in batch.iterate(batch_size=5):
# 		itr2.append(b)
# 		itr2.append(b.new())
# 		i += 1
# 	assert i == 2
#
# 	assert len(itr1) == len(itr2) == 4
#
# 	assert itr1[0]['target'][0].sum().isclose(itr2[0]['target'][0].sum())
# 	assert itr1[1]['target'][0].sum().isclose(itr2[1]['target'][0].sum())
# 	assert itr1[2]['target'][0].sum().isclose(itr2[2]['target'][0].sum())
# 	assert itr1[3]['target'][0].sum().isclose(itr2[3]['target'][0].sum())
#
#
#
# def test_simple_dataset():
#
# 	X, Y = torch.randn(100, 3), torch.randn(100, 1)
# 	dataset = od.SimpleDataset(X, Y)
#
# 	assert str(dataset) == 'SimpleDataset[100](0, 1)'
# 	assert dataset.size == 100
# 	assert dataset[0].sub(X).sum().item() == 0
#
# 	buffers = tuple(sorted(dataset.available_buffers()))
# 	assert len(buffers) == len(dataset)
# 	assert buffers == (0, 1)
#
# 	ds2 = od.SimpleDataset(X=X, Y=Y)
#
# 	assert str(ds2) == 'SimpleDataset[100](X, Y)'
# 	assert ds2.size == 100
# 	assert ds2['X'].sub(X).sum().item() == 0
#
# 	buffers = tuple(sorted(ds2.available_buffers()))
# 	assert len(buffers) == len(ds2)
# 	assert buffers == ('X', 'Y')















