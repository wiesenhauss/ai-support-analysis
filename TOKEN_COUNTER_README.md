# Real-time Token Counter Feature

## Overview
The Talk to Data feature now includes a real-time token counter that helps users monitor their context window usage when analyzing data with AI. This prevents API failures due to exceeding the 1 million token limit and provides transparency about data size.

## Visual Indicator

### Token Display
- **Location**: Bottom left of the Talk to Data window, next to the status
- **Format**: `123,456 / 1,000,000 (12.3%)`
- **Updates**: Real-time as you select/deselect columns

### Color Coding
- **🟢 Green (0-49%)**: Safe usage, no concerns
- **🟡 Yellow/Orange (50-89%)**: Moderate usage, monitor data size
- **🔴 Red (90%+)**: High usage, consider reducing data size

## How It Works

### Accurate Token Counting
- Uses `tiktoken` library for precise GPT-4 token counting
- Counts actual tokens, not just characters or words
- Accounts for tokenization differences in different languages

### Real-time Estimation
- **Column Selection**: Updates immediately when you check/uncheck columns
- **Data Size**: Estimates based on actual data sample
- **Prompt Structure**: Includes full analysis prompt in calculation

### Smart Sampling
- Automatically reduces data size if token limit approached
- Tries 5,000 → 3,000 → 1,000 rows progressively
- Logs all sampling decisions for transparency

## User Experience

### During Column Selection
1. **Initial Estimate**: Shows token count for AI-selected columns
2. **Interactive Updates**: Changes as you modify column selection
3. **Warning Logs**: Alerts when approaching limits
4. **Smart Recommendations**: Suggests reducing data size when needed

### During Analysis
1. **Pre-flight Check**: Validates token count before API call
2. **Automatic Fallback**: Reduces sample size if needed
3. **Progress Logging**: Shows actual tokens being sent
4. **Safety Margin**: Uses 95% of limit to prevent failures

## Technical Details

### Token Calculation
```python
# Base prompt + data estimation
base_tokens = count_tokens(analysis_prompt)
data_tokens = estimate_data_tokens(selected_columns, sample_size)
total_tokens = base_tokens + data_tokens
```

### Estimation Method
- Samples first 10 rows to calculate average tokens per row
- Multiplies by total sample size for accurate estimation
- Includes CSV formatting and column headers

### Safety Features
- **95% Safety Margin**: Stops at 950,000 tokens
- **Progressive Reduction**: Tries smaller samples automatically
- **Fallback Estimation**: Uses word count if tiktoken fails
- **Error Recovery**: Graceful handling of token counting errors

## Benefits

### For Users
- **Prevents Failures**: No more "context window exceeded" errors
- **Transparency**: See exactly how much context you're using
- **Optimization**: Make informed decisions about column selection
- **Confidence**: Know your analysis will complete successfully

### For Analysis Quality
- **Right-sized Data**: Optimal balance of data size and context limits
- **Consistent Results**: Predictable analysis completion
- **Better Performance**: Faster API responses with appropriate data sizes
- **Cost Efficiency**: Avoid wasted API calls from oversized requests

## Usage Tips

### Optimizing Token Usage
1. **Start with AI Selection**: The AI usually picks optimal columns
2. **Remove Large Text Columns**: Avoid full message bodies unless needed
3. **Focus on Key Metrics**: Prioritize high-value analytical columns
4. **Monitor the Counter**: Keep an eye on the percentage

### When You See Yellow/Orange (50-89%)
- Consider removing less important columns
- Check if large text fields are selected
- Review if all selected columns are necessary
- Analysis will still work but monitor closely

### When You See Red (90%+)
- Remove non-essential columns immediately
- Focus on core analytical fields only
- Consider asking a more focused question
- The system will auto-reduce data size if needed

## Troubleshooting

### Token Counter Shows 0
- Make sure columns are selected
- Check that a question has been entered
- Verify the CSV file loaded correctly

### Unexpectedly High Token Count
- Check for large text columns (like message bodies)
- Verify data sample size is reasonable
- Consider more focused column selection

### Analysis Still Fails Despite Green Counter
- Token estimation is approximate
- API limits can vary slightly
- System will automatically retry with smaller data

## Integration

### With Existing Features
- **Seamless Integration**: Works with all existing Talk to Data functionality
- **Logging Integration**: Token info appears in analysis log
- **Error Handling**: Integrated with existing error recovery
- **Build System**: Included in executable builds

### Dependencies
- **tiktoken**: Added to requirements.txt
- **Build Scripts**: Updated to include tiktoken
- **Verification**: Added to build verification checks

## Future Enhancements

### Potential Improvements
- **Model-specific Limits**: Different limits for different AI models
- **Token History**: Track token usage over time
- **Optimization Suggestions**: AI-powered column selection optimization
- **Batch Analysis**: Split large analyses into smaller chunks

---

*This feature ensures reliable, transparent, and efficient use of AI context windows for data analysis.* 