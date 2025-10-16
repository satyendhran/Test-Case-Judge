# **Test Case Judge**  
*A desktop application for testing programming solutions against input/output test cases with real-time execution monitoring and detailed result analysis.*

## **Overview**  
**Test Case Judge** is a PyQt5-based tool designed for competitive programmers and educators to efficiently validate code solutions. It supports *Python*, *C*, and *C++* programs, providing compilation, execution, and detailed comparison of outputs against expected answers.

## **Features**

### **Core Functionality**
- **Multi-Language Support:** Test *Python* (`.py`), *C* (`.c`), and *C++* (`.cpp`) solutions  
- **Automatic Compilation:** Built-in compiler integration for *C/C++* with optimization flags  
- **Batch Testing:** Run individual tests or execute all test cases simultaneously  
- **Real-Time Monitoring:** Live log display with timestamps and progress tracking  
- **Detailed Results:** View execution time, status, *stdout*, *stderr*, and line-by-line diffs  

### **User Interface**
- **Dark Theme:** Professional dark color scheme optimized for extended use  
- **Drag and Drop:** Quick solution file loading via drag-and-drop  
- **Split View:** Organized layout with test table, live logs, and detail panels  
- **Status Color Coding:** Visual indicators for **Accepted**, **Wrong Answer**, **TLE**, and **Runtime Errors**  
- **Report Export:** Save detailed test results to text files  

### **Test Management**
- **Flexible Input:** Add individual test pairs or import entire folders  
- **Input/Answer Pairing:** Automatic matching of `.in` and `.ans` files  
- **Selective Execution:** Run specific tests or the complete test suite  
- **Result Persistence:** Keep results across sessions for comparison  

## **Requirements**
- *Python 3.7* or higher  
- *PyQt5*  
- *GCC* (for C programs)  
- *G++* (for C++ programs)  

## **Installation**
```bash
pip install PyQt5
```

*Ensure GCC and G++ are installed and accessible from your system PATH for C/C++ support.*

## **Usage**

### **Getting Started**
1. Launch the application  
2. Select or drag-and-drop your solution file  
3. Add test cases using **"Add .in/.ans Pair"** or **"Add Folder"**  
4. Click **"Compile / Prepare"** for *C/C++* solutions  
5. Run tests using **"Run Selected"** or **"Run All"**  

### **Test Case Format**
Test cases consist of paired files:  
- `.in` files containing input data  
- `.ans` files containing expected output  

*Both files should have matching base names (e.g., `test01.in` and `test01.ans`).*

### **Compilation Settings**
- **C programs:** Compiled with `-O2 -std=c11`  
- **C++ programs:** Compiled with `-O2 -std=c++17`  
- **Python scripts:** Execute directly without compilation  

## **Result Status Types**
- **Accepted:** Output matches expected answer exactly  
- **Wrong Answer:** Output differs from expected answer  
- **TLE:** Execution exceeded time limit (default: 2 seconds)  
- **RE:** Runtime error or non-zero exit code  

## **Viewing Details**
Double-click any test row to view comprehensive details including:  
- **Execution status and time**  
- **Standard output and error streams**  
- **Line-by-line difference comparison**  

## **Keyboard and Mouse**
- Double-click table row: View test details  
- Drag files: Load solution quickly  
- Right-click: Context menu (standard Qt behavior)  

## **Limitations**
- Time limit is fixed at *2 seconds per test*  
- Requires exact output matching (*whitespace-sensitive*)  
- Compiled binaries are stored in the current working directory  
- No support for interactive problems  

## **Technical Details**

### **Architecture**
- Multi-threaded execution using `QThreadPool`  
- Asynchronous task execution with signal-slot communication  
- Separate worker threads prevent UI blocking during test runs  

### **File Handling**
- Temporary executable files created in working directory  
- Binary cleanup handled automatically  
- UTF-8 text encoding for all file operations  

## **Troubleshooting**
- Compilation fails: Verify *GCC/G++* installation anad PATH configuration  
- Tests don't run: Ensure solution file is selected and compiled (for C/C++)  
- Wrong Answer despite correct logic: Check for trailing whitespace or newline differences  
- Application won't start: Confirm *PyQt5* is properly installed  

## **License**
*This project is provided as-is for educational and personal use.*

## **Contributing**
Contributions are welcome. Consider adding features like:  
- Configurable time limits  
- Custom checker scripts  
- Memory usage monitoring  
- Batch solution testing  
- Test case generation tools  

*Developed with PyQt5 for an efficient competitive programming workflow.*
