# Talk to Data Feature - User Guide

## Overview
The "Talk to Data" feature allows you to ask natural language questions about your processed customer support data and get AI-powered insights. This feature uses GPT-4.1 to analyze your data and provide comprehensive answers.

## How to Use

### 1. Prerequisites
- Load a processed CSV file that contains "support-analysis-output-predictive-csat" in the filename
- Ensure you have a valid OpenAI API key configured

### 2. Accessing the Feature
- Click the "💬 Talk to Data" button in the main application window
- The button will only be enabled when a compatible CSV file is loaded

### 3. Using the Interface
The Talk to Data window provides an integrated experience with several sections:

#### Question Input
- Enter your question in natural language in the text area
- Click "🔍 Analyze Question" to start the analysis
- Use "💡 Examples" to see sample questions

#### Column Selection (Auto-displayed)
- After question analysis, AI will automatically select relevant columns
- Review the AI's reasoning displayed at the top
- Modify column selection using checkboxes if needed
- Click "🚀 Proceed with Analysis" to continue

#### Real-time Logging
- Monitor the analysis progress in the "Analysis Log" section
- See detailed information about:
  - Data preparation steps
  - AI processing status
  - Column selection details
  - Error messages and troubleshooting info

#### Results Display
- View comprehensive analysis results in markdown format
- Results include executive summary, detailed analysis, key metrics, and recommendations
- Click "💾 Save Results" to save the analysis to a file

### 4. Data Sampling
The feature automatically handles large datasets:
- **≤5,000 rows**: Uses full dataset
- **>5,000 rows**: Uses random sample of 5,000 rows
- **API limits**: Automatically reduces to 3,000 or 1,000 rows if needed
- All sampling is logged for transparency

## Example Questions

### Customer Satisfaction Analysis
- "What are the main factors affecting customer satisfaction scores?"
- "Which product areas have the lowest CSAT scores and why?"
- "How do satisfaction scores vary by customer segment?"

### Support Performance
- "What are the most common customer issues and how quickly are they resolved?"
- "Which support agents or teams have the best performance metrics?"
- "What's the relationship between response time and customer satisfaction?"

### Product Insights
- "What are customers saying about our new features?"
- "Which products generate the most support tickets?"
- "What are the top feature requests from customers?"

### Trend Analysis
- "How have support metrics changed over the past quarter?"
- "Are there seasonal patterns in customer issues?"
- "What trends do you see in customer feedback?"

## Features

### Intelligent Column Selection
- AI analyzes your question and selects the most relevant data columns
- Prioritizes high-value columns while avoiding large text fields when possible
- Provides reasoning for column selection
- Allows manual adjustment of selected columns

### Comprehensive Analysis
The AI provides structured analysis including:
- **Executive Summary**: Key findings in 2-3 sentences
- **Detailed Analysis**: In-depth insights with specific data points
- **Key Metrics**: Important numbers and percentages
- **Actionable Recommendations**: Specific steps based on findings
- **Supporting Evidence**: Data points that support conclusions

### Real-time Progress Tracking
- Live logging of all analysis steps
- Progress indicators and status updates
- Detailed error messages for troubleshooting
- Data size and processing information

### Smart Data Handling
- Automatic data sampling for large datasets
- Context window management for API calls
- Fallback strategies for API limitations
- Random sampling to ensure representative data

## Technical Details

### Supported Data Formats
- CSV files with "support-analysis-output-predictive-csat" in filename
- Automatically detects and uses column metadata
- Supports 25+ predefined support data columns

### AI Model
- Uses GPT-4.1 for both question analysis and data analysis
- Optimized prompts for customer support analytics
- Temperature set to 0.3 for consistent, analytical responses

### Data Privacy
- All data processing happens through OpenAI's API
- No data is stored permanently by the application
- Results are only saved locally when you choose to save them

## Troubleshooting

### Common Issues

**"Talk to Data" button is disabled**
- Ensure your CSV file contains "support-analysis-output-predictive-csat" in the filename
- Check that the file loaded successfully in the main application

**Analysis fails with context errors**
- The system automatically reduces data size and retries
- Check the log for details about data sampling
- Very large datasets may need manual column reduction

**API errors**
- Verify your OpenAI API key is valid and has sufficient credits
- Check your internet connection
- API rate limits may require waiting before retrying

**No results displayed**
- Check the Analysis Log for error details
- Ensure your question is clear and specific
- Try rephrasing your question or selecting different columns

### Getting Better Results

**Write Clear Questions**
- Be specific about what you want to analyze
- Mention specific metrics or dimensions you're interested in
- Ask one focused question at a time

**Review Column Selection**
- The AI's column selection is usually good, but you can adjust it
- Include relevant categorical columns for grouping
- Include relevant numeric columns for calculations

**Interpret Results**
- Results are based on the data sample used
- Consider the sampling method when interpreting findings
- Use results as insights to guide further investigation

## File Output

Results are saved in markdown format with:
- Timestamp and question asked
- Columns analyzed and dataset information
- Complete AI analysis with formatting
- Metadata about the analysis process

Files are saved with timestamp: `talktodata-YYYYMMDD-HHMMSS.txt`

## Integration

The Talk to Data feature is fully integrated with the main AI Support Analyzer:
- Shares the same OpenAI API key
- Works with the same processed data files
- Maintains consistent UI design and workflow
- Provides seamless user experience

---

*This feature is part of the AI Support Analyzer application and requires processed customer support data to function.* 