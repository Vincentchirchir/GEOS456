#Variable
#assigning interger value to a variable
age=25
#assigning string value to a variable
name="Vincent"
#float
height=57
#boolean value
is_student=True

print(age)
print(name)
print(height)
print(is_student)

#Variable and strings
first_name="Vincent"
last_name="Chirchir"
full_name=f"{first_name} {last_name}"
print("My name is: ", full_name)
greeting=f"Hello, my name is {full_name} and I am {age} years old"
print(greeting)
print("")

#indexingin strings
text='Hellow world!'

print(text[0])
print("")

#accessing from list
numbers=[10, 20, 30, 40, 50]
print(numbers[0])
print("")

#slicing
#slicing allows you to access a rangee of elements in a sequence
numbers=[10, 20, 30, 40, 50]
print(numbers[1:4])
print(numbers[::2])
print(numbers[2:])
print("")

#modifying lists using indexing
numbers=[10, 20, 30, 40, 50]
numbers[0]=15
print(numbers)
numbers[1:3] = [34, 98]
print(numbers)