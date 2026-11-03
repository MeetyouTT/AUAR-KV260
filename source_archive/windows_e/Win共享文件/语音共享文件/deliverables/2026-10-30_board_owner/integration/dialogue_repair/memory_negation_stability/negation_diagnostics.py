"""Optional pure numeric diagnostics for a future root-reviewed instrumented run.

These categories describe word forms. They never decide whether to publish a
summary, infer a private statement's meaning, or replace any existing check.
"""
import re

ALTERNATIVE_FORMS = re.compile(r'能不能|会不会|是不是|有没有')
CANDIDATE_FORMS = {
    'inability':re.compile(r'无法|未能'),
    'difference':re.compile(r'不同|有别'),
    'pending_or_unperformed':re.compile(r'未校准|未购买|未执行|未确认|尚待|仍待'),
    'other_negative':re.compile(r'并非|并未|从未|未曾'),
}


def negation_diagnostics(sources, summary, negation_pattern):
    """Return a fixed schema of counts without text, IDs, hashes or matches."""
    result = dict(source_events=0, invalid_sources=0, truncated_sources=0,
        source_regex_matches=0, source_metadata_negated=0,
        source_alternative_form_matches=0, source_guard_matches_in_alternative_forms=0,
        source_guard_matches_outside_alternative_forms=0,
        candidate_regex_matches=0, candidate_alternative_form_matches=0,
        candidate_utf8_bytes=0, invalid_candidate=False,
        candidate_form_counts={key:0 for key in CANDIDATE_FORMS})
    if not isinstance(sources,(list,tuple)):
        result['invalid_sources']=1
        sources=()
    result['truncated_sources']=max(0,len(sources)-64)
    for source in sources[:64]:
        if not isinstance(source,dict) or source.get('include_in_summary') is not True:
            result['invalid_sources']+=1
            continue
        text=source.get('text')
        metadata=source.get('metadata')
        if not isinstance(text,str) or len(text)>32768 or not isinstance(metadata,dict):
            result['invalid_sources']+=1
            continue
        result['source_events']+=1
        result['source_metadata_negated']+=metadata.get('negated') is True
        alternatives=list(ALTERNATIVE_FORMS.finditer(text))
        result['source_alternative_form_matches']+=len(alternatives)
        for match in negation_pattern.finditer(text):
            result['source_regex_matches']+=1
            inside=any(phrase.start()<=match.start() and match.end()<=phrase.end() for phrase in alternatives)
            if inside:
                result['source_guard_matches_in_alternative_forms']+=1
            else:
                result['source_guard_matches_outside_alternative_forms']+=1
    if not isinstance(summary,str) or len(summary)>8192:
        result['invalid_candidate']=True
        return result
    result['candidate_regex_matches']=sum(1 for _ in negation_pattern.finditer(summary))
    result['candidate_alternative_form_matches']=sum(1 for _ in ALTERNATIVE_FORMS.finditer(summary))
    result['candidate_utf8_bytes']=len(summary.encode('utf8'))
    result['candidate_form_counts']={key:sum(1 for _ in pattern.finditer(summary))
                                     for key,pattern in CANDIDATE_FORMS.items()}
    return result
