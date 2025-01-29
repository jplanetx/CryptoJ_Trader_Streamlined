# Implementation Threads and Prompts

## Thread Management

### Update Logging
Each thread implementation should create an update log in the Updates directory:
```
Updates/thread_[thread_number]_[YYYYMMDD_HHMM].txt

Format:
Thread: [thread_number]
Step: [step_number]
Status: [Completed/In Progress/Review Required]
Changes Made:
- [List of specific changes]
Validation:
- [List of validation steps completed]
Next Steps:
- [List of next steps if any]
```

### Review Process
A separate review thread should be created for each implementation thread:
```
Role: You are Roo, a code review specialist focused on minimal viable implementations.

Task:
1. Review implementation of Thread [X]
2. Verify completion criteria
3. Validate changes against requirements
4. Check for potential issues
5. Provide specific feedback

Context:
- Review update logs
- Check code changes
- Verify test coverage
- Assess documentation

Deliverable: Detailed review report with specific recommendations
```

## Thread 1: Core Trading Setup
**Role**: Code Implementation
**Focus**: Basic Trading Core Setup

### Step 1.1: Trading Core Simplification
**Prompt**:
```
Role: You are Roo, a trading systems expert focused on minimal viable implementations.

Task:
1. Simplify trading_core.py to essential components:
   - Basic order execution
   - Simple position tracking
   - Health monitoring
2. Remove unnecessary classes (TechnicalAnalysis, TradingStrategy)
3. Implement basic error handling
4. Add essential logging

Context:
- Working from minimal-viable-trader branch
- Focus on single trading pair initially
- Maintain core safety features

Best Practices:
- Keep code simple and readable
- Focus on reliability
- Implement proper error handling
- Add clear logging

Completion Criteria:
1. Code Structure:
   - TradingBot class only
   - Essential methods identified and documented
   - Unused classes removed
   
2. Core Functionality:
   - Order execution method implemented
   - Position tracking implemented
   - Basic health checks added
   
3. Error Handling:
   - Critical errors identified
   - Recovery procedures implemented
   - Logging added for all errors
   
4. Documentation:
   - Method documentation complete
   - Error scenarios documented
   - Configuration requirements documented

5. Testing:
   - Basic unit tests passing
   - Core functionality verified
   - Error handling tested

Validation Steps:
1. Run unit tests
2. Verify logging output
3. Test error scenarios
4. Check documentation completeness

Deliverable: 
1. Updated trading_core.py with minimal essential functionality
2. Update log with specific changes
3. Test results documentation
```

[Previous thread content remains unchanged...]

## Review Thread Template
**Role**: Code Review Specialist
**Focus**: Implementation Validation

### Review Process
1. **Pre-review Checklist**:
   - Collect all update logs
   - Review code changes
   - Check test results
   - Review documentation

2. **Review Areas**:
   - Code quality and simplification
   - Error handling completeness
   - Documentation quality
   - Test coverage
   - Security considerations

3. **Validation Steps**:
   - Verify completion criteria
   - Check best practices adherence
   - Validate error handling
   - Review logging implementation

4. **Output Format**:
```
# Implementation Review Report

## Thread: [Number]
## Step: [Number]
## Date: [YYYY-MM-DD]

### Review Summary
- Overall Status: [Complete/Incomplete/Needs Revision]
- Critical Issues: [Yes/No]
- Documentation Status: [Complete/Incomplete]

### Detailed Findings
1. Code Quality
   - [Specific observations]
   - [Recommendations]

2. Functionality
   - [Verification results]
   - [Issues found]

3. Error Handling
   - [Coverage assessment]
   - [Improvement needs]

4. Documentation
   - [Completeness check]
   - [Clarity assessment]

### Recommendations
1. [Specific recommendation]
2. [Specific recommendation]
3. [Specific recommendation]

### Next Steps
1. [Required action]
2. [Required action]
3. [Required action]
```

## Implementation Flow

[Previous implementation flow content remains unchanged...]

## Thread Management Guidelines

[Previous guidelines content remains unchanged...]