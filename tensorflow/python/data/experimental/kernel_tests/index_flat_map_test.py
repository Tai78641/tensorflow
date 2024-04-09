# Copyright 2024 The TensorFlow Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================
"""Tests for the index flat map dataset."""

from typing import Any, Union

from absl.testing import parameterized

from tensorflow.python.data.experimental.ops import index_flat_map_op
from tensorflow.python.data.kernel_tests import test_base
from tensorflow.python.data.ops import dataset_ops
from tensorflow.python.framework import combinations
from tensorflow.python.framework import constant_op
from tensorflow.python.framework import dtypes
from tensorflow.python.framework import tensor
from tensorflow.python.ops import array_ops
from tensorflow.python.ops import math_ops
from tensorflow.python.ops.ragged import ragged_string_ops
from tensorflow.python.platform import test

_IndexType = index_flat_map_op._IndexType


class IndexFlatMapTest(test_base.DatasetTestBase, parameterized.TestCase):
  """Tests for global shuffling of tf.data datasets."""

  @combinations.generate(
      combinations.times(
          test_base.default_test_combinations(),
          combinations.combine(use_tensors=[True, False])))
  def test_split_strings(self, use_tensors: bool):
    input_data = ["0 1", "2 3 4 5", "6 7", "8"]
    metadata = constant_op.constant(
        [(0, 2, 0), (2, 6, 1), (6, 8, 2), (8, 9, 3)], dtype=dtypes.int64)

    def _split(element: str) -> tensor.Tensor:
      return ragged_string_ops.string_split_v2(element, " ")

    def _index_map_func(index: _IndexType) -> tuple[_IndexType, _IndexType]:
      element_index = _maybe_convert_to_tensor(0)
      while (element_index < metadata.shape[0] and
             index >= array_ops.gather_nd(metadata, [element_index, 1])):
        element_index += 1
      offset = (
          index - array_ops.gather_nd(metadata, [element_index, 0])
          if element_index < metadata.shape[0]
          else constant_op.constant(0, dtype=dtypes.int64))
      return (_maybe_convert_to_tensor(element_index),
              _maybe_convert_to_tensor(offset))

    def _maybe_convert_to_tensor(value: Any) -> Union[int, tensor.Tensor]:
      return math_ops.cast(value, dtypes.int64) if use_tensors else value

    dataset = dataset_ops.Dataset.from_tensor_slices(input_data)
    dataset = index_flat_map_op.index_flat_map(dataset, _split, _index_map_func)
    output = self.getDatasetOutput(dataset)
    self.assertEqual(output,
                     [b"0", b"1", b"2", b"3", b"4", b"5", b"6", b"7", b"8"])

  @combinations.generate(
      combinations.times(
          test_base.default_test_combinations(),
          combinations.combine(dataset_range=[0, 10])))
  def test_identity_map(self, dataset_range: int):

    def _map_func(element: Any) -> Any:
      return element

    def _index_map_func(index: int) -> tuple[int, int]:
      return (index, 0)

    dataset = dataset_ops.Dataset.range(dataset_range)
    dataset = index_flat_map_op.index_flat_map(
        dataset, _map_func, _index_map_func)
    self.assertDatasetProduces(dataset, list(range(dataset_range)))


if __name__ == "__main__":
  test.main()