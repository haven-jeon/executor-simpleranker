__copyright__ = "Copyright (c) 2020-2021 Jina AI Limited. All rights reserved."
__license__ = "Apache-2.0"

from itertools import groupby
from typing import Dict

from docarray.score import NamedScore
from jina import DocumentArray, Executor, requests, Document
from jina.logging.logger import JinaLogger


class SimpleRanker(Executor):
    """
    :class:`SimpleRanker` aggregates the score of the matched doc from the
        matched chunks. For each matched doc, the score is aggregated from all the
        matched chunks belonging to that doc. The score of the document is the minimum
        score (min distance) among the chunks. The aggregated matches are sorted by
        score (ascending).
    """

    def __init__(
        self,
        metric: str = 'cosine',
        ranking: str = 'min',
        traversal_paths: str = '@r',
        *args,
        **kwargs,
    ):
        """
        :param metric: the distance metric used in `scores`
        :param renking: The ranking function that the executor uses. There are multiple
            options:
            - min: Select minimum score/distance and sort by minimum
            - max: Select maximum score/distance and sort by maximum
            - mean_min: Calculate mean score/distance and sort by minimum mean
            - mean_max: Calculate mean score/distance and sort by maximum mean
        :param traversal_paths: traverse path on docs, e.g. ['r'], ['c']
        """
        super().__init__(*args, **kwargs)
        self.logger = JinaLogger('ranker')
        self.metric = metric
        assert ranking in ['min', 'max', 'mean_min', 'mean_max']
        self.ranking = ranking
        self.logger.warning(f'ranking = {self.ranking}')
        self.traversal_paths = traversal_paths

    @requests(on='/search')
    def rank(self, docs: DocumentArray, parameters: Dict, *args, **kwargs):
        traversal_paths = parameters.get('traversal_paths', self.traversal_paths)

        for doc in docs[traversal_paths]:
            matches_of_chunks = []
            matches_of_chunks.extend(doc.matches)
            doc.matches.clear()
            for chunk in doc.chunks:
                matches_of_chunks.extend(chunk.matches)
            groups = groupby(
                sorted(matches_of_chunks, key=lambda d: d.parent_id or d.id),
                lambda d: d.parent_id or d.id,
            )
            for key, group in groups:
                chunk_match_list = list(group)
                if self.ranking == 'min':
                    chunk_match_list = DocumentArray(
                        sorted(
                            chunk_match_list, key=lambda m: m.scores[self.metric].value
                        )
                    )
                elif self.ranking == 'max':
                    chunk_match_list = DocumentArray(
                        sorted(
                            chunk_match_list, key=lambda m: -m.scores[self.metric].value
                        )
                    )
                # more robust way to copy Document
                match = Document()
                match.copy_from(chunk_match_list[0])
                # only replace if not root node
                if match.granularity > 0:
                    match.id = chunk_match_list[0].parent_id
                    match.granularity = 0
                    match.parent_id = None
                if self.ranking in ['mean_min', 'mean_max']:
                    scores = [el.scores[self.metric].value for el in chunk_match_list]
                    match.scores[self.metric] = NamedScore(
                        value=sum(scores) / len(scores), op_name=self.ranking
                    )
                doc.matches.append(match)
            if self.ranking in ['min', 'mean_min']:
                doc.matches = DocumentArray(
                    sorted(doc.matches, key=lambda d: d.scores[self.metric].value)
                )
            elif self.ranking in ['max', 'mean_max']:
                doc.matches = DocumentArray(
                    sorted(doc.matches, key=lambda d: -d.scores[self.metric].value)
                )
