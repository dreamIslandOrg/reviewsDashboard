import json, random, datetime
random.seed(7)
domains = ["אוכל ומסעדה","ניקיון","חדרים ונוחות","בריכה ומתקנים","ספא","אירועים","צוות ושירות","קבלה וצ'ק אין","מחיר ותמורה","אווירה ומיקום","פעילויות ובידור","אחר"]
praise_w = [31,15,8,24,18,2,33,5,7,40,16,6]
comp_w   = [39,8,5,15,9,1,18,5,28,8,8,2]
months = [("2026-07",17,(12,4,1)),("2026-08",27,(21,5,1)),("2026-09",50,(29,10,11)),("2026-10",43,(18,13,12)),("2026-11",25,(16,6,3))]
def base(y,m):
    d=datetime.date(int(y),int(m),11 if m=="07" else 1)
    return (d-datetime.date(1899,12,30)).days
texts={"חיובית":"מקום מקסים, הבריכות החמות מעולות והצוות אדיב מאוד. נחזור שוב.",
       "מעורבת":"היה נעים מאוד והספא מצוין, אבל האוכל בפודטראקים חלש והמחיר גבוה ביחס למה שמקבלים.",
       "שלילית":"התאכזבנו מאוד. האוכל היה קר, היה עומס גדול בכל הדוכנים, והשירות לא היה ברמה שמצפים לה במחיר כזה. פנינו לקבלה ולא קיבלנו מענה של ממש, ולכן לא נחזור. חבל, כי לפני שנתיים המקום היה ברמה אחרת לגמרי."}
rows=[]; n=0
for ym,cnt,(p,mx,ng) in months:
    y,m=ym.split("-")
    for i,c in enumerate(["חיובית"]*p+["מעורבת"]*mx+["שלילית"]*ng):
        n+=1
        r={"חיובית":random.choice([5,5,5,4]),"מעורבת":random.choice([3,4,5,2]),"שלילית":random.choice([1,1,2,3])}[c]
        has_text = random.random()<0.7 or c!="חיובית"
        pr = random.choices(domains,weights=praise_w,k=random.randint(0,3)) if has_text and c!="שלילית" else []
        co = random.choices(domains,weights=comp_w,k=random.randint(1,3)) if c!="חיובית" and has_text else []
        rows.append([f"id{n}", base(y,m)+i*0.6, f"אורח לדוגמה {n}", r, texts[c] if has_text else "", c,
                     "נושא לדוגמה", ", ".join(dict.fromkeys(pr)), ", ".join(dict.fromkeys(co)),
                     random.choice(["כן","לא","לא"]), "ייבוא", ""])
json.dump({"rows":rows,"google":[4.300000190734863,5588,"2026-11-11 12:05"],"domains":domains},
          open("dev/fixture.json","w"),ensure_ascii=False)
print(len(rows))
