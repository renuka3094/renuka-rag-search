from app.services.chunking import chunk_sections


def test_short_section_becomes_one_chunk():
    sections = [("PTO Policy", "Employees accrue 1.5 days per month. Unused days roll over up to 5 days.")]
    chunks = chunk_sections(sections)
    assert len(chunks) == 1
    assert chunks[0].section_heading == "PTO Policy"
    assert "accrue" in chunks[0].content


def test_long_section_splits_with_overlap():
    long_text = " ".join([f"Sentence number {i} about benefits." for i in range(200)])
    sections = [("Benefits Overview", long_text)]
    chunks = chunk_sections(sections)
    assert len(chunks) > 1
    # every chunk should respect the configured token budget (with slack for the final sentence)
    for c in chunks:
        assert c.token_count <= 420


def test_ordinal_increases_across_sections():
    sections = [("A", "First section text."), ("B", "Second section text.")]
    chunks = chunk_sections(sections)
    ordinals = [c.ordinal for c in chunks]
    assert ordinals == sorted(ordinals)


def test_empty_section_produces_no_chunks():
    sections = [("Empty", "")]
    chunks = chunk_sections(sections)
    assert chunks == []
