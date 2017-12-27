功能：从邮箱A接收邮件并过滤，然后将用户关心的邮件再转发给邮箱B，这样可以用终端监听邮箱B，只接收自己关心的邮件，免得被打扰。

filter.xml格式如下：
```
<!--过滤规则为: 1)只留下匹配leave后的邮件； 2)从留下的邮件中删除匹配discard的邮件-->
<!--匹配规则: from, to, cc, subject, content 全匹配才算配置一个leave或discard--->

<!--leave first then discard-->
<!--<item>-->
    <!--<from>邮件发送者</from>: 邮件发送者包含此字符串即可-->
    <!--<to>邮件接收者</to>: 邮件接收者包含此字符串即可-->
    <!--<cc>邮件抄送者</cc>: 邮件抄送者包含此字符串即可-->
    <!--<subject>邮件主题</subject>: 邮件主题包含此字符串即可-->
    <!--<content>邮件内容</content>: 邮件内容包含此字符串即可-->
<!--</item>-->

<filter>
    <leave>
        <item>
            <to>hello@fuckyou.com</to>
        </item>
        <item>
            <to>hi@fuckyou.com</to>
        </item>
    </leave>
    <discard>
        <item>
            <subject>how to fuck</subject>
        </item>
        <item>
            <subject>no-subject</subject>
        </item>
        <item>
            <from>no@fuckyou.com</from>
            <subject>good</subject>
        </item>
    </discard>
</filter>
```
