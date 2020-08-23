from powertools import Transform
from powertools import config

from powertools.exceptions import PowertoolsCycleException
from powertools.exceptions import PowertoolsDuplicateTransformException

from typing import List
from typing import Dict

import importlib
import pkgutil
import time
from collections import deque

import logging

logger = logging.getLogger(__name__)


# A graph is a dictionary of transforms (keys) to a list of transformations (value) which have
# outputs that are inputs to given transform (key).
Graph = Dict[Transform, List[Transform]]


class Pipeline:
    """A pipeline is a topologically ordered list of transforms."""

    def __init__(self, transforms: List[Transform] = []):
        self.transforms = transforms

    @property
    def tasks(self):
        if len(set(self.transforms)) != len(self.transforms):
            raise PowertoolsDuplicateTransformException(f"Duplicate {self.transforms}")
        return _get_tasks(self.transforms)  # Topologically sort the transforms.

    def __repr__(self):
        return (
            'Pipeline(\n    -> '
            + '\n    -> '.join(map(str, self.transforms))
            + '\n)'
        )

    def run(self):
        """Used to run all the transforms in the pipeline.

        Returns:
            Dict[str, Any]: Metadata about the run of the pipeline.
        """
        completed = set()
        pipeline_run_data = []
        logger.info(repr(self))
        logger.info(f'BEGINNING RUNNING OF {self}.')
        for transform in self.tasks:
            run_data = {}
            run_data['transform'] = repr(transform)

            # Run the transform.
            start = time.time()
            if transform not in completed:
                try:
                    transform.run()
                    run_data['transform_message'] = 'SUCCES'
                except Exception as exception:
                    if config.ENVIRONMENT == 'TESTING':
                        raise exception
                    logger.exception(f'FAILED RUNNING OF {transform}.')
                    run_data['transform_message'] = str(exception)
            else:
                if config.ENVIRONMENT == 'TESTING':
                    raise ValueError(f'Duplicate {self.transforms}')
                logger.error(f'DUPLICATE {transform}.')
                run_data['transform_message'] = 'DUPLICATE'
            run_data['transform_time'] = time.time() - start

            # Save data about the transform run.
            completed.add(transform)
            pipeline_run_data.append(run_data)
        logger.info(f'COMPLETED RUNNING OF {self}.')
        return pipeline_run_data

    @classmethod
    def discover_transforms(cls, *plugins):
        """Find and import all transforms in plugins.

        This function will automatically disover transforms from plugins
        using namespace packages e.g. fixed namespace(s), as defined by
        the input plugins args to the function, where plugins are saved.

        Args:
            *plugins (module): Module(s) that contains transforms.

        Returns:
            Pipeline: A pipeline of the discovered transforms.

        References:
            [1] https://packaging.python.org/guides/creating-and-discovering-plugins/
        """
        transforms = []
        for plugin in plugins:

            if isinstance(plugin, Transform):
                logger.info(f"DISCOVERED {plugin} as plugin input.")
                transforms.append(plugin)
                continue

            for _, name, ispkg in pkgutil.walk_packages(
                path=plugin.__path__,
                prefix=plugin.__name__ + ".",
            ):
                plugin_module = importlib.import_module(name)
                for attrname in dir(plugin_module):
                    new_attr = getattr(plugin_module, attrname)
                    if isinstance(new_attr, Transform):
                        logger.info(f"DISCOVERED {new_attr} in {name}.")
                        transforms.append(new_attr)
        return cls(transforms)


def _get_tasks(transforms: List[Transform]) -> List[Transform]:
    """Get the tasks in order of execution.

    Args:
        transforms (List[Transform]): A list of transforms to be topologically ordered.

    Returns:
        List[Transforms]: A topologically ordered list of transforms s.t. the output of
            a transform cannot be the input to a previous transform in the list.
    """
    graph = _create_graph(transforms)
    tasks = _tsort(graph)
    return tasks


def _create_graph(transforms: List[Transform]) -> Graph:
    """Create a graph out of a list of transforms.

    The graph is encoded as a dict of {from: List[to]}, where from and to are
    transforms.

    Args:
        transforms (List[Transform]): A list of transforms.

    Returns:
        Graph: The list of transforms encoded as a graph. A graph is a dictionary of
            transforms (keys) to a list of transformations (value) which have outputs
            that are inputs to given transform (key).
    """
    return {
        from_:
        [
            to for to in transforms
            if any(
                output in to.inputs for output in from_.outputs
            )
        ]
        for from_ in transforms
    }


def _tsort(graph: Graph) -> List[Transform]:
    """Used to sort a directed acyclic graph of tasks in order of execution.

    Args:
        graph (Dict[Transform, List(Transform)]): A list of output transforms
            to inputs.

    Returns:
        List(Transform): A list of transforms sorted in order of execution.

    References:
        [1] https://algocoding.wordpress.com/2015/04/05/topological-sorting-python/
    """
    in_degree = {u: 0 for u in graph}     # determine in-degree
    for u in graph:                       # of each node
        for v in graph[u]:
            in_degree[v] += 1

    Q = deque()                 # collect nodes with zero in-degree
    for u in in_degree:
        if in_degree[u] == 0:
            Q.appendleft(u)

    L = []     # list for order of nodes

    while Q:
        u = Q.pop()          # choose node of zero in-degree
        L.append(u)          # and 'remove' it from graph
        for v in graph[u]:
            in_degree[v] -= 1
            if in_degree[v] == 0:
                Q.appendleft(v)

    if len(L) == len(graph):
        return L
    else:                    # if there is a cycle,
        raise PowertoolsCycleException("Cycle detected in the DAG.")
