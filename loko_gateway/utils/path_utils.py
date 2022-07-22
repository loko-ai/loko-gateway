def common_prefix(texts):
	i=0
	pref=[]
	cand=None
	while True:
		for t in texts:
			if len(t)>i:
				if cand and t[i]!=cand:
					return pref
				else:
					cand=t[i]
			else:
				return pref
		i+=1
		pref.append(cand)
		cand=None

def to_relative(u):
	if u.startswith("/"):
		return u[1:]
	else:
		return u