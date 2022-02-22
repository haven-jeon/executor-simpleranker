__copyright__ = "Copyright (c) 2021 Jina AI Limited. All rights reserved."
__license__ = "Apache-2.0"

import pytest
from simpleranker import SimpleRanker


@pytest.mark.parametrize('traversal_paths', ['@r', '@c'])
@pytest.mark.parametrize('ranking', ['min', 'max'])
def test_ranking(documents_chunk, documents_chunk_chunk, traversal_paths, ranking):
    ranker = SimpleRanker(
        metric='cosine',
        ranking=ranking,
        traversal_paths=traversal_paths,
    )
    if traversal_paths == '@r':
        ranking_docs = documents_chunk
    else:
        ranking_docs = documents_chunk_chunk

    ranker.rank(ranking_docs, parameters={})
    assert ranking_docs

    for doc in ranking_docs[traversal_paths]:
        assert doc.matches
        for i in range(len(doc.matches) - 1):
            match = doc.matches[i]
            assert match.tags
            if ranking == 'min':
                assert (
                    match.scores['cosine']
                    <= doc.matches[i + 1].scores['cosine']
                )
            else:
                assert (
                    match.scores['cosine']
                    >= doc.matches[i + 1].scores['cosine']
                )


@pytest.mark.parametrize('ranking', ['mean_min', 'mean_max'])
def test_mean_ranking(documents_chunk, ranking):
    traversal_paths = '@r'
    ranker = SimpleRanker(
        metric='cosine',
        ranking=ranking,
        traversal_paths=traversal_paths,
    )
    ranking_docs = documents_chunk

    mean_scores = []
    for doc in ranking_docs[0].chunks:
        scores = []
        for match in doc.matches:
            scores.append(match.scores['cosine'])
        mean_scores.append(sum(scores) / 10)
    mean_scores.sort(reverse=ranking == 'mean_max')
    ranker.rank(ranking_docs, parameters={})
    assert ranking_docs

    for doc in ranking_docs[traversal_paths]:
        assert doc.matches
        for i in range(len(doc.matches) - 1):
            match = doc.matches[i]
            assert match.tags
            assert match.scores['cosine'] == pytest.approx(mean_scores[i], 1e-5)
