# Preference smoke archive

These documents record the early 12-case Preference engineering smoke. They
are retained because they explain two design decisions that still matter:

- benchmark-facing inputs use one language so embedding-language quality is
  not confused with memory quality;
- mem0's Qdrant data and history SQLite database must both be isolated per
  case to prevent cross-case leakage.

The smoke case JSON and intermediate result JSONs are intentionally no longer
part of the active dataset. The frozen 30-case pilot supersedes them. Paths to
those deleted artifacts in the historical notes are evidence labels, not
reproduction links.
