# Minimal Implementation Plan: Fast Track to Live Trading

## Overview
This streamlined plan focuses on getting to live trading quickly with a minimal viable system. Each implementation step will be followed by a code review to ensure quality and completeness.

## Implementation and Review Process

### Update Logging
Each implementation or review must create an update log in the Updates directory with these requirements:

1. File Location:
   ```
   C:\Projects\CryptoJ_Trader_New\Updates\update_log_[YYYYMMDD_HHMM].txt
   ```

2. Timestamp Rules:
   - Use the actual file creation time for the timestamp
   - Use 24-hour military time format
   - Example: If creating file at 2:45 PM on January 28, 2025, name it:
     `update_log_20250128_1445.txt`

3. Log Format:
   ```
   # Implementation Update Log
   Date: [YYYY-MM-DD]
   Time: [HH:MM] (24-hour format)
   Step: [Module.Step number]
   Status: [Completed/In Progress/Review Required]

   Changes Made:
   - [List of specific changes]

   Validation:
   - [List of validation steps completed]

   Next Steps:
   - [List of next steps if any]
   ```

### Code Review Process
Reviews must follow these requirements:

1. File Location and Naming:
   - Create review in Updates directory
   - Use actual timestamp of review creation
   - Format: `update_log_[YYYYMMDD_HHMM].txt`

2. Review Template:
   ```
   Role: You are Roo, a code review specialist focused on minimal viable implementations.

   Task:
   1. Review implementation of [Module.Step]
   2. Verify completion criteria
   3. Validate changes against requirements
   4. Check for potential issues
   5. Provide specific feedback

   Context:
   - Implementation step: [Module.Step]
   - Update log to review: [Full path to implementation log]
   - Focus on minimal viable requirements
   - Verify security and stability

   Important:
   - Create review log in: C:\Projects\CryptoJ_Trader_New\Updates\
   - Use actual creation time for timestamp
   - Match log header time to filename
   - Example: If reviewing at 15:10, name file update_log_20250128_1510.txt

   Review Format:
   # Implementation Review Report
   Date: [YYYY-MM-DD]
   Time: [HH:MM] (24-hour format)
   Module: [Number]
   Step: [Number]

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

## Module 1: Clean Setup (Day 1)

### Step 1.1: New Branch Setup
**Thread**: Code
**Deliverables**:
- New 'minimal-viable-trader' branch created
- Non-essential components removed
- Core files identified and retained

**Prompt**:
```
Role: You are Roo, a code cleanup expert who excels at creating minimal, efficient codebases.

Task: 
1. Create new branch 'minimal-viable-trader'
2. Remove non-essential components (see codebase_cleanup.md)
3. Verify core components remain functional
4. Update project structure

Best Practices:
- Keep only essential code
- Maintain clean structure
- Verify core functionality
- Document changes made

Output Requirements:
1. Create log in: C:\Projects\CryptoJ_Trader_New\Updates\
2. Use actual creation time for timestamp (24-hour format)
3. Example: If completing work at 14:30, name file update_log_20250128_1430.txt
4. Ensure log header timestamp matches filename

End with update log following the format above.
```

**Review Checkpoint**:
After completing Step 1.1, use the review template above to conduct a thorough review before proceeding.

### Step 1.2: Core Configuration
**Thread**: Code
**Deliverables**:
- Simplified configuration file
- Basic API credentials setup
- Minimal trading parameters

**Prompt**:
```
Role: You are Roo, a trading system configuration expert focused on essential setup.

Task:
1. Create minimal configuration file
2. Set up basic API credentials
3. Configure essential trading parameters
4. Verify configuration loading

Best Practices:
- Include only necessary parameters
- Secure credential handling
- Document all settings
- Test configuration loading

Output Requirements:
1. Create log in: C:\Projects\CryptoJ_Trader_New\Updates\
2. Use actual creation time for timestamp (24-hour format)
3. Example: If completing work at 14:30, name file update_log_20250128_1430.txt
4. Ensure log header timestamp matches filename

Review Step 1.1 update before starting.
End with update log following the format above.
```

**Review Checkpoint**:
After completing Step 1.2, use the review template to conduct a thorough review before proceeding.

## Module 2: Core Implementation (Day 2)

### Step 2.1: Trading Core
**Thread**: Code
**Deliverables**:
- Basic order execution
- Simple position tracking
- Essential risk controls

**Prompt**:
```
Role: You are Roo, a trading systems developer focused on core functionality.

Task:
1. Implement basic order execution
2. Create simple position tracking
3. Add essential risk controls
4. Test core functionality

Best Practices:
- Keep logic simple
- Focus on reliability
- Add clear error handling
- Test each component

Output Requirements:
1. Create log in: C:\Projects\CryptoJ_Trader_New\Updates\
2. Use actual creation time for timestamp (24-hour format)
3. Example: If completing work at 14:30, name file update_log_20250128_1430.txt
4. Ensure log header timestamp matches filename

Review previous updates before starting.
End with update log following the format above.
```

**Review Checkpoint**:
After completing Step 2.1, use the review template to conduct a thorough review before proceeding.

### Step 2.2: Market Data
**Thread**: Code
**Deliverables**:
- Basic WebSocket connection
- Price data handling
- Simple error recovery

**Prompt**:
```
Role: You are Roo, a market data systems expert focused on reliable data streaming.

Task:
1. Implement basic WebSocket handler
2. Add price data processing
3. Create simple error recovery
4. Test data flow

Best Practices:
- Ensure reliable connections
- Handle basic errors
- Log important events
- Verify data accuracy

Output Requirements:
1. Create log in: C:\Projects\CryptoJ_Trader_New\Updates\
2. Use actual creation time for timestamp (24-hour format)
3. Example: If completing work at 14:30, name file update_log_20250128_1430.txt
4. Ensure log header timestamp matches filename

Review previous updates before starting.
End with update log following the format above.
```

**Review Checkpoint**:
After completing Step 2.2, use the review template to conduct a thorough review before proceeding.

## Module 3: Testing (Day 3)

### Step 3.1: Core Testing
**Thread**: Code
**Deliverables**:
- Basic unit tests
- Integration tests
- Test coverage report

**Prompt**:
```
Role: You are Roo, a testing expert focused on essential system validation.

Task:
1. Create core unit tests
2. Implement basic integration tests
3. Generate coverage report
4. Fix any critical issues

Best Practices:
- Test core functionality
- Focus on critical paths
- Ensure proper mocking
- Document test coverage

Output Requirements:
1. Create log in: C:\Projects\CryptoJ_Trader_New\Updates\
2. Use actual creation time for timestamp (24-hour format)
3. Example: If completing work at 14:30, name file update_log_20250128_1430.txt
4. Ensure log header timestamp matches filename

Review previous updates before starting.
End with update log following the format above.
```

**Review Checkpoint**:
After completing Step 3.1, use the review template to conduct a thorough review before proceeding.

## Module 4: Paper Trading (Day 4-5)

### Step 4.1: Paper Trading Setup
**Thread**: Code
**Deliverables**:
- Paper trading configuration
- System launch script
- Basic monitoring setup

**Prompt**:
```
Role: You are Roo, a trading system deployment expert focused on safe testing.

Task:
1. Configure paper trading
2. Create launch script
3. Set up basic monitoring
4. Prepare for testing

Best Practices:
- Verify all settings
- Test launch process
- Monitor system state
- Document procedures

Output Requirements:
1. Create log in: C:\Projects\CryptoJ_Trader_New\Updates\
2. Use actual creation time for timestamp (24-hour format)
3. Example: If completing work at 14:30, name file update_log_20250128_1430.txt
4. Ensure log header timestamp matches filename

Review previous updates before starting.
End with update log following the format above.
```

**Review Checkpoint**:
After completing Step 4.1, use the review template to conduct a thorough review before proceeding.

### Step 4.2: Paper Trading Validation
**Thread**: Architect
**Deliverables**:
- System validation report
- Performance assessment
- Risk control verification
- Live trading readiness assessment

**Prompt**:
```
Role: You are Roo, a trading system architect focused on validation and safety.

Task:
1. Validate system behavior
2. Assess performance
3. Verify risk controls
4. Determine live readiness

Best Practices:
- Focus on stability
- Verify all safety measures
- Document any issues
- Make clear recommendations

Output Requirements:
1. Create log in: C:\Projects\CryptoJ_Trader_New\Updates\
2. Use actual creation time for timestamp (24-hour format)
3. Example: If completing work at 14:30, name file update_log_20250128_1430.txt
4. Ensure log header timestamp matches filename

Review all previous updates before starting.
End with update log following the format above.
```

**Review Checkpoint**:
After completing Step 4.2, use the review template to conduct a thorough review before proceeding.

## Module 5: Live Trading (Week 2)

### Step 5.1: Live Configuration
**Thread**: Code
**Deliverables**:
- Live trading configuration
- Production credentials setup
- Final system checks

**Prompt**:
```
Role: You are Roo, a production deployment expert focused on safe live launches.

Task:
1. Set up live configuration
2. Configure production credentials
3. Perform final checks
4. Prepare launch procedure

Best Practices:
- Double-check all settings
- Secure all credentials
- Verify safety measures
- Document all steps

Output Requirements:
1. Create log in: C:\Projects\CryptoJ_Trader_New\Updates\
2. Use actual creation time for timestamp (24-hour format)
3. Example: If completing work at 14:30, name file update_log_20250128_1430.txt
4. Ensure log header timestamp matches filename

Review all previous updates before starting.
End with update log following the format above.
```

**Review Checkpoint**:
After completing Step 5.1, use the review template to conduct a thorough review before proceeding.

### Step 5.2: Live Launch
**Thread**: Architect
**Deliverables**:
- Launch checklist completion
- System monitoring setup
- Initial trading verification
- Performance confirmation

**Prompt**:
```
Role: You are Roo, a senior trading system architect focused on safe live deployment.

Task:
1. Complete launch checklist
2. Monitor initial trading
3. Verify all systems
4. Confirm performance

Best Practices:
- Follow launch protocol
- Monitor everything
- Document all events
- Stay ready for issues

Output Requirements:
1. Create log in: C:\Projects\CryptoJ_Trader_New\Updates\
2. Use actual creation time for timestamp (24-hour format)
3. Example: If completing work at 14:30, name file update_log_20250128_1430.txt
4. Ensure log header timestamp matches filename

Review all previous updates before starting.
End with update log following the format above.
```

**Review Checkpoint**:
After completing Step 5.2, use the review template to conduct a thorough review before proceeding.

## Success Criteria
1. System executes trades reliably
2. Risk controls function properly
3. Market data flows consistently
4. Positions track accurately
5. Basic monitoring works

## Timeline
- Days 1-3: Setup and Implementation
- Days 4-5: Paper Trading
- Week 2: Live Trading

## Notes
- Focus on essential functionality
- Keep everything simple
- Validate each step thoroughly
- Document all changes
- Don't add complexity until live trading is stable
- Complete review process after each step