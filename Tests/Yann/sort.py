def sor(mot1, mot2):
    if mot1.sort() == mot2.sort():
        return True
    else:
        return False

mot1 = input("Entrez un mot: ")
mot2 = input("Entrez un autre mot: ")

print(sor(mot1, mot2))