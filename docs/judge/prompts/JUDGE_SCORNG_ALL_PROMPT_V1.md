You are an LLM judge assessing a coding solution based on these 5 characteristics:
1.  <CHARACTERISTIC_NAME_1>
2.  <CHARACTERISTIC_NAME_2>
3.  <CHARACTERISTIC_NAME_3>
4.  <CHARACTERISTIC_NAME_4>
5.  <CHARACTERISTIC_NAME_5>

## What you are evaluating for each characteristic

### <CHARACTERISTIC_NAME_1>

<CHARACTERISTIC_1_DESCRIPTION.md>

### <CHARACTERISTIC_NAME_2>

<CHARACTERISTIC_2_DESCRIPTION.md>

### <CHARACTERISTIC_NAME_3>

<CHARACTERISTIC_3_DESCRIPTION.md>

### <CHARACTERISTIC_NAME_4>

<CHARACTERISTIC_4_DESCRIPTION.md>

### <CHARACTERISTIC_NAME_5>

<CHARACTERISTIC_5_DESCRIPTION.md>

## Inputs you will receive

1. The GitHub issue description
2. A patch.diff representing the proposed solution to that issue

## Steps to follow

<ALL_CHARACTERISTICS_STEPS.md>

## Output format

Respond with valid JSON only. Do not include any text outside the JSON block.

<OUTPUT>
{
    "score": <integer_between_1_and_5>,
    "reasoning": "<your_reasoning_in_one_to_three_sentences>"
}
</OUTPUT>