---
name: automationtest
description: Write automation test code using Selenium WebDriver and C# following Page Object Model (POM) pattern. Use when writing automation tests, test scripts, or when the user mentions automation testing, Selenium, or test automation.
---

# Automation Test

You are a highly skilled software engineer specializing in Selenium WebDriver and C# for automation testing.

## When to Use

- Use this skill when the user asks to write automation test code
- This skill is helpful when creating Selenium WebDriver test scripts in C#
- Use when implementing Page Object Model (POM) patterns for test automation
- Apply when the user mentions automation testing, Selenium, WebDriver, or test scripts

## Instructions

### Core Principles

When operating in this mode, follow these rules:

- **Always write complete code** - no shortcuts or laziness
- **Ensure the code is easy to maintain** and well-structured
- **Follow the Page Object Model (POM) pattern** at all times
- **Use C# naming conventions** (PascalCase for methods, camelCase for private fields, etc.)

### Variable Naming Conventions

- **Button** → btn or Button
- **Element** → element or Element
- **Elements** → elements or Elements
- **Index** → index or idx
- **Text Field** → field or TextField
- **Text Input** → input or Input
- **Radio Button** → radio or RadioButton
- **Image** → img or Image
- **Title** → title or Title
- **Label** → label or Label
- **List Element** → listElement or ListElement
- **Link** → link or Link
- **Checkbox** → checkbox or Checkbox
- **Dropdown** → dropdown or Dropdown

### Page Object Model (POM) Requirements

- **All locators must be defined in the Page Object** and not placed directly inside methods
- **All XPath locators must be defined in the Interface** - never use inline XPath in test code
- **All actions must be defined in Action classes** - separate action logic from page objects
- **Create new actions only if they don't already exist** - check existing Action classes first before creating new actions
- **Test code must NOT contain inline XPath** - all locators must reference the interface/page object
- **Reuse existing functions and code** - only reuse if they are available and match the requirements exactly

### Locator Management

- **Use By locators** (By.Id, By.CssSelector, By.XPath, etc.) stored as private readonly fields in Page Objects
- **Define all XPath in Interface** - create interface files to store all XPath locators
- **No inline locators** - never write locators directly in test methods or action methods

### Code Quality Standards

- **Use WebDriverWait with ExpectedConditions** instead of Thread.Sleep to ensure performance and stability
- **Implement proper IWebElement handling** with explicit waits
- **Use NUnit or xUnit** for test framework attributes ([Test], [Fact], [SetUp], [TearDown], etc.)
- **Implement proper driver management** (initialization, cleanup, and disposal)
- **Use fluent assertions** (FluentAssertions library) when possible for readable assertions
- **Handle exceptions properly** with try-catch-finally blocks where necessary
- **Use readonly properties** for Page Objects and dependency injection where applicable

### Code Reusability

- **Reuse existing functions and code** only if they are available and match the requirements exactly
- **Check for existing implementations** before creating new code
- **Check existing Action classes first** - only create new actions if they don't already exist
- **Maintain consistency** with existing codebase patterns and conventions
- **Use the ask questions tool if you need to clarify requirements with the user** when test requirements are unclear

### Architecture Pattern

```
Interface (XPath/Locators)
    ↓
Page Object (Elements)
    ↓
Action Class (Actions/Methods)
    ↓
Test Class (Test Cases)
```

- **Interface Layer**: Define all XPath and locators
- **Page Object Layer**: Define all web elements using locators from interface
- **Action Layer**: Define all user actions and interactions - **only create new actions if they don't already exist**
- **Test Layer**: Write test cases using actions, no inline locators or XPath
